"""Everything that touches the operating system.

Circle runs on Windows and macOS, and the two disagree about almost every
system call: volume, screenshots, locking the screen, enumerating windows,
starting at login. This module is the single place that knows which one it is
running on. Everything else in the app asks for the behaviour, not the API.

Every function degrades quietly: on a platform it does not support, it returns
a sensible value and prints why, rather than raising into a UI callback.
"""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
import time
import urllib.parse
import webbrowser
from typing import List, Optional

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = not (IS_WINDOWS or IS_MACOS)

PLATFORM = "windows" if IS_WINDOWS else ("macos" if IS_MACOS else "linux")

CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0

LAUNCH_AGENT_LABEL = "com.circle.launcher"


# ------------------------------------------------------------------ plumbing ---

def run(args, shell=False, timeout=None) -> bool:
    """Fire and forget, with no console flash on Windows.

    Returns False only when the process could not be started at all.
    """
    try:
        proc = subprocess.Popen(
            args, shell=shell, creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        if timeout:
            proc.wait(timeout=timeout)
        return True
    except Exception as exc:
        print(f"[circle] failed to run {args!r}: {exc}")
        return False


def capture(args, timeout=6) -> str:
    """Run something and read its output. Never raises."""
    try:
        done = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
        return (done.stdout or "").strip()
    except Exception as exc:
        print(f"[circle] command failed {args!r}: {exc}")
        return ""


def osascript(script: str) -> str:
    if not IS_MACOS:
        return ""
    return capture(["osascript", "-e", script])


# ---------------------------------------------------------------- files/urls ---

def open_path(path: str) -> bool:
    """Open a file, folder, shortcut or app bundle.

    Returns False when nothing could be started, so the caller can tell the
    user instead of appearing to do nothing.
    """
    if IS_WINDOWS:
        try:
            os.startfile(path)  # noqa: S606 - intentional shell open
            return True
        except OSError as exc:
            # ShellExecute refuses some targets that the shell itself resolves
            # (broken associations, shortcuts in odd locations). Try once more
            # through cmd's start before giving up.
            print(f"[circle] startfile failed for {path}: {exc}")
        if run(["cmd", "/c", "start", "", path]):
            return True
        return False

    if IS_MACOS:
        return run(["open", path])
    return run(["xdg-open", path])


def reveal_path(path: str) -> bool:
    """Show the item in the file manager rather than opening it."""
    if IS_WINDOWS:
        if os.path.isdir(path):
            return run(["explorer.exe", path])
        return run(["explorer.exe", "/select,", os.path.normpath(path)])
    if IS_MACOS:
        if os.path.isdir(path):
            return run(["open", path])
        return run(["open", "-R", path])
    return run(["xdg-open", os.path.dirname(path) or "."])


def open_url(url: str) -> bool:
    try:
        return bool(webbrowser.open(url))
    except Exception as exc:
        print(f"[circle] cannot open url {url}: {exc}")
        return False


# ------------------------------------------------------------------- volume ---

def get_volume() -> int:
    if IS_MACOS:
        raw = osascript("output volume of (get volume settings)")
        try:
            return max(0, min(100, int(float(raw))))
        except ValueError:
            return 50
    if IS_WINDOWS:
        try:
            from action_executor import get_system_volume
            return get_system_volume()
        except Exception:
            return 50
    return 50


def set_volume(percent: int) -> int:
    target = max(0, min(100, int(round(percent))))
    if IS_MACOS:
        osascript(f"set volume output volume {target}")
        return target
    if IS_WINDOWS:
        try:
            from action_executor import set_system_volume_percent
            return set_system_volume_percent(target)
        except Exception:
            return target
    return target


def change_volume(delta: int) -> int:
    return set_volume(get_volume() + delta)


def is_muted() -> bool:
    if IS_MACOS:
        return osascript("output muted of (get volume settings)").strip() == "true"
    return False


def toggle_mute() -> bool:
    if IS_MACOS:
        muted = is_muted()
        osascript(f"set volume output muted {'false' if muted else 'true'}")
        return not muted
    if IS_WINDOWS:
        try:
            from action_executor import toggle_system_mute
            return toggle_system_mute()
        except Exception:
            return False
    return False


# -------------------------------------------------------------------- media ---

_MAC_PLAYERS = ["Music", "Spotify", "VLC"]


def media_control(action: str):
    """playpause / next / prev."""
    if IS_MACOS:
        for player in _MAC_PLAYERS:
            state = osascript(
                f'tell application "System Events" to (name of processes) contains "{player}"'
            )
            if state.strip().lower() != "true":
                continue
            if action == "playpause":
                osascript(f'tell application "{player}" to playpause')
            elif action == "next":
                osascript(f'tell application "{player}" to next track')
            elif action == "prev":
                osascript(f'tell application "{player}" to previous track')
            return
        print("[circle] no supported media player is running")
        return
    if IS_WINDOWS:
        try:
            from action_executor import execute_slot_action
            execute_slot_action({"action_type": "media", "action_detail": action})
        except Exception as exc:
            print(f"[circle] media control failed: {exc}")


# -------------------------------------------------------------------- power ---

def lock_screen():
    if IS_MACOS:
        # The login-window helper needs no permissions; AppleScript is the fallback.
        helper = ("/System/Library/CoreServices/Menu Extras/User.menu/Contents/"
                  "Resources/CGSession")
        if os.path.exists(helper):
            run([helper, "-suspend"])
        else:
            osascript('tell application "System Events" to keystroke "q" '
                      'using {control down, command down}')
        return
    if IS_WINDOWS:
        run(["rundll32.exe", "user32.dll,LockWorkStation"])
    else:
        run(["loginctl", "lock-session"])


def sleep_machine():
    if IS_MACOS:
        run(["pmset", "sleepnow"])
    elif IS_WINDOWS:
        run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
    else:
        run(["systemctl", "suspend"])


def sign_out():
    if IS_MACOS:
        osascript('tell application "System Events" to log out')
    elif IS_WINDOWS:
        run(["shutdown", "/l"])


def show_desktop():
    if IS_MACOS:
        # F11 by default; Mission Control key codes vary, so use the menu item.
        osascript('tell application "System Events" to key code 103')
    elif IS_WINDOWS:
        try:
            from pynput.keyboard import Controller, Key
            kb = Controller()
            with kb.pressed(Key.cmd):
                kb.press("d")
                kb.release("d")
        except Exception as exc:
            print(f"[circle] show desktop failed: {exc}")


def empty_trash():
    if IS_MACOS:
        osascript('tell application "Finder" to empty trash')
    elif IS_WINDOWS:
        run(["powershell", "-NoProfile", "-Command",
             "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"])


# ------------------------------------------------------------------- capture ---

def screenshot():
    """Region capture, copied to the clipboard."""
    if IS_MACOS:
        run(["screencapture", "-i", "-c"])
    elif IS_WINDOWS:
        run(["cmd", "/c", "start", "", "ms-screenclip:"])


def snip():
    screenshot()


# --------------------------------------------------------------------- apps ---

def open_terminal():
    if IS_MACOS:
        run(["open", "-a", "Terminal"])
    elif IS_WINDOWS:
        run(["wt.exe"])
    else:
        run(["x-terminal-emulator"])


def open_task_manager():
    if IS_MACOS:
        run(["open", "-a", "Activity Monitor"])
    elif IS_WINDOWS:
        run(["taskmgr.exe"])


def open_activity_monitor():
    open_task_manager()


def open_settings():
    if IS_MACOS:
        run(["open", "-b", "com.apple.systempreferences"])
    elif IS_WINDOWS:
        run(["cmd", "/c", "start", "", "ms-settings:"])


def open_settings_uri(uri: str):
    """Deep link into a settings page. Best effort on both platforms."""
    if IS_MACOS:
        run(["open", uri])
    elif IS_WINDOWS:
        run(["cmd", "/c", "start", "", uri])
    else:
        open_url(uri)


# ------------------------------------------------------------------ windows ---

def list_windows() -> List[dict]:
    """Top-level windows: [{'handle', 'title', 'app'}]."""
    if IS_MACOS:
        return _mac_list_windows()
    if IS_WINDOWS:
        return _win_list_windows()
    return []


def activate_window(handle):
    if IS_MACOS:
        _mac_activate(handle)
    elif IS_WINDOWS:
        _win_activate(handle)


_MAC_SKIP_OWNERS = {
    "Window Server", "Dock", "Control Center", "Notification Center",
    "Spotlight", "Circle", "SystemUIServer", "TextInputMenuAgent",
}


def _mac_list_windows() -> List[dict]:
    try:
        import Quartz
    except Exception as exc:
        print(f"[circle] window list needs pyobjc-framework-Quartz: {exc}")
        return []

    try:
        options = (Quartz.kCGWindowListOptionOnScreenOnly
                   | Quartz.kCGWindowListExcludeDesktopElements)
        raw = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID) or []
    except Exception as exc:
        print(f"[circle] cannot read the window list: {exc}")
        return []

    windows: List[dict] = []
    seen = set()
    for item in raw:
        if item.get("kCGWindowLayer") != 0:
            continue
        owner = (item.get("kCGWindowOwnerName") or "").strip()
        if not owner or owner in _MAC_SKIP_OWNERS:
            continue
        pid = item.get("kCGWindowOwnerPID")
        # kCGWindowName is empty without Screen Recording permission; the app
        # name still gives a usable result in that case.
        title = (item.get("kCGWindowName") or "").strip() or owner
        key = (pid, title)
        if key in seen:
            continue
        seen.add(key)
        windows.append({"handle": int(pid), "title": title, "app": owner,
                        "proc_path": _mac_bundle_path(pid)})
    return windows


def _mac_bundle_path(pid) -> str:
    """The .app the process belongs to, for its icon."""
    try:
        from AppKit import NSRunningApplication
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(int(pid))
        url = app.bundleURL() if app is not None else None
        return url.path() if url is not None else ""
    except Exception:
        return ""


def _mac_activate(pid):
    try:
        from AppKit import NSRunningApplication
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(int(pid))
        if app is not None:
            # NSApplicationActivateIgnoringOtherApps = 1 << 1
            app.activateWithOptions_(2)
            return
    except Exception as exc:
        print(f"[circle] AppKit activation unavailable ({exc}); using AppleScript")

    osascript(f'tell application "System Events" to set frontmost of '
              f'(first process whose unix id is {int(pid)}) to true')


def _win32():
    """Configure the Win32 prototypes once.

    Without argtypes ctypes assumes c_int for every argument and return value,
    which truncates 64-bit HWNDs and HANDLEs. That silently broke window
    activation and leaked a process handle on every enumeration.
    """
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL

    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL

    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int

    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int

    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long

    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND,
                                                ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD

    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.restype = wintypes.BOOL
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL

    user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD,
                                   ctypes.POINTER(wintypes.ULONG)]
    user32.keybd_event.restype = None
    user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
    user32.AllowSetForegroundWindow.restype = wintypes.BOOL

    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD)]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    return user32, kernel32


_WIN32 = None


def _win32_cached():
    global _WIN32
    if _WIN32 is None:
        _WIN32 = _win32()
    return _WIN32


_WIN_SKIP_TITLES = {"Program Manager", "Windows Input Experience", "Task View",
                    "Default IME", "MSCTFIME UI", "Circle", "Search"}


def _win_process_path(kernel32, pid: int) -> str:
    import ctypes
    from ctypes import wintypes

    handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(1024)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return buffer.value
        return ""
    finally:
        # Always close: the old code leaked one handle per window per refresh.
        kernel32.CloseHandle(handle)


def _win_list_windows() -> List[dict]:
    import ctypes
    from ctypes import wintypes

    user32, kernel32 = _win32_cached()
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    windows: List[dict] = []

    @callback_type
    def _callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title or title in _WIN_SKIP_TITLES:
            return True
        if user32.GetWindowLongW(hwnd, -20) & 0x00000080:  # WS_EX_TOOLWINDOW
            return True

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        path = _win_process_path(kernel32, pid.value)
        windows.append({
            "handle": int(hwnd),
            "title": title,
            "app": os.path.splitext(os.path.basename(path))[0] if path else "",
            "proc_path": path,
            "pid": pid.value,
        })
        return True

    try:
        user32.EnumWindows(_callback, 0)
    except Exception as exc:
        print(f"[circle] window enumeration failed: {exc}")
    return windows


def focus_own_window(handle):
    """Bring one of our own windows to the front.

    Windows refuses SetForegroundWindow to a process that did not recently
    receive input, which is exactly our case: the hotkey arrives through a
    global hook. A synthetic Alt tap satisfies the check.
    """
    if not IS_WINDOWS:
        return
    import ctypes
    from ctypes import wintypes

    user32, _kernel32 = _win32_cached()
    try:
        user32.AllowSetForegroundWindow(0xFFFFFFFF)  # ASFW_ANY
        user32.keybd_event(0x12, 0, 0, None)         # VK_MENU down
        user32.keybd_event(0x12, 0, 2, None)         # VK_MENU up
        user32.SetForegroundWindow(wintypes.HWND(int(handle)))
        user32.BringWindowToTop(wintypes.HWND(int(handle)))
    except Exception as exc:
        print(f"[circle] cannot raise our window: {exc}")


def _win_activate(hwnd):
    user32, _kernel32 = _win32_cached()
    try:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)      # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
    except Exception as exc:
        print(f"[circle] cannot focus window {hwnd}: {exc}")


# ------------------------------------------------------------- text/dictation ---

def trigger_dictation() -> bool:
    """Start system dictation. Returns False when it has to be done by hand."""
    if IS_MACOS:
        return _mac_trigger_dictation()
    if IS_WINDOWS:
        try:
            from pynput.keyboard import Controller, Key
            keyboard = Controller()
            with keyboard.pressed(Key.cmd):
                keyboard.press("h")
                keyboard.release("h")
            return True
        except Exception as exc:
            print(f"[circle] dictation shortcut failed: {exc}")
    return False


def _mac_trigger_dictation() -> bool:
    """macOS starts dictation on a double press of the fn/globe key."""
    try:
        import Quartz
    except Exception:
        return False
    try:
        for _ in range(2):
            for down in (True, False):
                event = Quartz.CGEventCreateKeyboardEvent(None, 63, down)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
            time.sleep(0.06)
        return True
    except Exception as exc:
        print(f"[circle] could not post the dictation key: {exc}")
        return False


# ------------------------------------------------------------------ autostart ---

def set_autostart(enable: bool = True):
    if IS_MACOS:
        _mac_set_autostart(enable)
    elif IS_WINDOWS:
        try:
            from action_executor import set_autostart as _win_set
            _win_set(enable)
        except Exception as exc:
            print(f"[circle] autostart failed: {exc}")


def get_autostart() -> bool:
    if IS_MACOS:
        return os.path.exists(_mac_plist_path())
    if IS_WINDOWS:
        try:
            from action_executor import get_autostart as _win_get
            return _win_get()
        except Exception:
            return False
    return False


def _mac_plist_path() -> str:
    return os.path.expanduser(f"~/Library/LaunchAgents/{LAUNCH_AGENT_LABEL}.plist")


def _mac_launch_command() -> List[str]:
    """The command that starts Circle, whether frozen or run from source."""
    if getattr(sys, "frozen", False):
        bundle = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", ".."))
        if bundle.endswith(".app"):
            return [os.path.join(bundle, "Contents", "MacOS", "Circle")]
        return [sys.executable]
    entry = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    return [sys.executable, entry]


def _mac_set_autostart(enable: bool):
    path = _mac_plist_path()
    if not enable:
        if os.path.exists(path):
            run(["launchctl", "unload", "-w", path])
            try:
                os.remove(path)
            except OSError as exc:
                print(f"[circle] could not remove the login item: {exc}")
        return

    payload = {
        "Label": LAUNCH_AGENT_LABEL,
        "ProgramArguments": _mac_launch_command(),
        "RunAtLoad": True,
        "ProcessType": "Interactive",
        "LimitLoadToSessionType": "Aqua",
    }
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            plistlib.dump(payload, fh)
        run(["launchctl", "load", "-w", path])
    except Exception as exc:
        print(f"[circle] could not write the login item: {exc}")


# ---------------------------------------------------------------- shortcuts ---

_MAC_SYMBOLS = {
    "ctrl": "\u2303", "control": "\u2303",
    "alt": "\u2325", "option": "\u2325", "opt": "\u2325",
    "shift": "\u21e7",
    "cmd": "\u2318", "command": "\u2318", "win": "\u2318", "super": "\u2318",
}
_WIN_NAMES = {
    "ctrl": "Ctrl", "control": "Ctrl",
    "alt": "Alt", "option": "Alt", "opt": "Alt",
    "shift": "Shift",
    "cmd": "Win", "command": "Win", "win": "Win", "super": "Win",
}
_KEY_NAMES = {
    "space": "Space", "enter": "Enter", "return": "Return", "tab": "Tab",
    "esc": "Esc", "escape": "Esc", "backspace": "Backspace", "delete": "Del",
    "up": "\u2191", "down": "\u2193", "left": "\u2190", "right": "\u2192",
}


def format_shortcut(spec: str) -> str:
    """'<ctrl>+<alt>+<space>' -> '\u2303\u2325Space' on macOS, 'Ctrl + Alt + Space' on Windows."""
    text = (spec or "").strip()
    if not text:
        return ""
    if text.lower() in ("middle_click", "middle click", "button.middle"):
        return "Middle click"

    tokens = [t.strip() for t in text.replace("<", "+").replace(">", "+").split("+")]
    tokens = [t for t in tokens if t]
    modifiers = _MAC_SYMBOLS if IS_MACOS else _WIN_NAMES

    parts = []
    for token in tokens:
        key = token.lower()
        if key in modifiers:
            parts.append(modifiers[key])
        elif key in _KEY_NAMES:
            parts.append(_KEY_NAMES[key])
        elif len(token) == 1:
            parts.append(token.upper())
        else:
            parts.append(token.title())

    if IS_MACOS:
        # macOS convention: modifiers packed together, no separators.
        return "".join(parts)
    return " + ".join(parts)


def shortcut_presets() -> List[tuple]:
    """(label, spec) pairs that make sense on this platform."""
    if IS_MACOS:
        return [
            ("\u2325Space", "<alt>+<space>"),
            ("\u2303\u2325Space", "<ctrl>+<alt>+<space>"),
            ("\u2303Space", "<ctrl>+<space>"),
        ]
    return [
        ("Alt + Space", "<alt>+<space>"),
        ("Ctrl + Space", "<ctrl>+<space>"),
        ("Ctrl + K", "<ctrl>+k"),
    ]


def footer_hints() -> str:
    """The key legend under the search panel, written the platform's way."""
    if IS_MACOS:
        return "\u2191\u2193  navigate     \u21b5  open     \u21e7\u21b5  reveal     esc  close"
    return "\u2191\u2193  navigate     \u21b5  open     shift+\u21b5  reveal     esc  close"


# ------------------------------------------------------------------ helpers ---

def encode_query(text: str) -> str:
    return urllib.parse.quote_plus(text)


def platform_notes() -> List[str]:
    """What this platform needs from the user, shown in the README and UI."""
    if IS_MACOS:
        return [
            "Accessibility permission for global shortcuts and window control",
            "Screen Recording permission for window titles in Search",
        ]
    if IS_WINDOWS:
        return ["Nothing beyond a normal install"]
    return ["Running on Linux: system actions are limited"]
