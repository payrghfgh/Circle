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

def run(args, shell=False, timeout=None) -> Optional[str]:
    """Fire and forget, with no console flash on Windows."""
    try:
        proc = subprocess.Popen(
            args, shell=shell, creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        if timeout:
            proc.wait(timeout=timeout)
        return None
    except Exception as exc:
        print(f"[circle] failed to run {args!r}: {exc}")
        return None


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

def open_path(path: str):
    if IS_WINDOWS:
        try:
            os.startfile(path)  # noqa: S606 - intentional shell open
            return
        except Exception as exc:
            print(f"[circle] cannot open {path}: {exc}")
            return
    if IS_MACOS:
        run(["open", path])
    else:
        run(["xdg-open", path])


def reveal_path(path: str):
    """Show the item in the file manager rather than opening it."""
    if IS_WINDOWS:
        if os.path.isdir(path):
            run(["explorer.exe", path])
        else:
            run(["explorer.exe", "/select,", os.path.normpath(path)])
    elif IS_MACOS:
        if os.path.isdir(path):
            run(["open", path])
        else:
            run(["open", "-R", path])
    else:
        run(["xdg-open", os.path.dirname(path) or "."])


def open_url(url: str):
    try:
        webbrowser.open(url)
    except Exception as exc:
        print(f"[circle] cannot open url {url}: {exc}")


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
        windows.append({"handle": int(pid), "title": title, "app": owner})
    return windows


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


def _win_list_windows() -> List[dict]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD

    ignored = {"Program Manager", "Windows Input Experience", "Task View",
               "Default IME", "MSCTFIME UI", "Circle", "Search"}
    windows: List[dict] = []

    @WNDENUMPROC
    def _callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title or title in ignored:
            return True
        ex_style = user32.GetWindowLongW(hwnd, -20)
        if ex_style & 0x00000080:  # WS_EX_TOOLWINDOW
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        windows.append({
            "handle": hwnd,
            "title": title,
            "app": _win_process_name(kernel32, pid.value),
            "pid": pid.value,
        })
        return True

    try:
        user32.EnumWindows(_callback, 0)
    except Exception as exc:
        print(f"[circle] window enumeration failed: {exc}")
    return windows


def _win_process_name(kernel32, pid: int) -> str:
    try:
        handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            return ""
        import ctypes
        size = ctypes.c_ulong(1024)
        buffer = ctypes.create_unicode_buffer(1024)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            name = os.path.splitext(os.path.basename(buffer.value))[0]
            kernel32.CloseHandle(handle)
            return name
        kernel32.CloseHandle(handle)
    except Exception:
        pass
    return ""


def _win_activate(hwnd):
    import ctypes
    user32 = ctypes.windll.user32
    try:
        user32.ShowWindow(hwnd, 9)          # SW_RESTORE
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
