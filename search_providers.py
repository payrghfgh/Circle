"""What Circle can find.

Every provider returns the same small `Result` object, so the window stays
dumb: it renders what it is handed and runs the callable on Enter.

Sources, in the order they matter to someone who just hit the hotkey:
calculator, open windows, installed apps, files, system actions, Windows
settings pages, and the web as a fallback that is always there.
"""

from __future__ import annotations

import ast
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional

from PySide6.QtCore import QFileInfo, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileIconProvider

import config
import platform_layer as platform

IS_WINDOWS = platform.IS_WINDOWS
IS_MACOS = platform.IS_MACOS

CREATE_NO_WINDOW = platform.CREATE_NO_WINDOW


# ------------------------------------------------------------------ model ---

@dataclass
class Result:
    title: str
    kind: str = ""
    subtitle: str = ""
    icon: str = "file"
    icon_path: str = ""
    score: float = 0.0
    run: Optional[Callable[[], None]] = None
    alt_run: Optional[Callable[[], None]] = None
    alt_hint: str = ""
    key: str = ""

    @property
    def group(self) -> str:
        return self.kind or "Results"


GROUP_ORDER = ["Calculator", "Windows", "Apps", "Files", "Folders", "Actions",
               "Settings", "Web"]


# ------------------------------------------------------------------- utils ---

def _spawn(args, shell=False) -> bool:
    try:
        subprocess.Popen(args, shell=shell, creationflags=CREATE_NO_WINDOW,
                         close_fds=True)
        return True
    except Exception as exc:  # pragma: no cover - platform dependent
        print(f"[circle] failed to run {args!r}: {exc}")
        return False


# Thin wrappers rather than aliases: binding the function object at import time
# means later changes to the platform layer never reach these call sites.
def open_path(path: str) -> bool:
    return platform.open_path(path)


def reveal_path(path: str) -> bool:
    return platform.reveal_path(path)


def open_url(url: str) -> bool:
    return platform.open_url(url)


def score_text(query: str, text: str) -> float:
    """Rank a candidate string against the query.

    Prefix beats word-start beats substring beats initials beats subsequence,
    and every tier is shortened by how far into the string the match lands.
    """
    if not query:
        return 1.0
    q = query.lower().strip()
    t = text.lower()
    if not q or not t:
        return 0.0

    if t.startswith(q):
        return 100.0 - min(len(t), 60) * 0.15

    idx = t.find(q)
    if idx >= 0:
        boundary = idx > 0 and t[idx - 1] in " -_./\\()[]"
        if boundary:
            return 90.0 - min(idx, 40) * 0.2
        return 72.0 - min(idx, 40) * 0.25

    words = [w for w in re.split(r"[\s\-_./\\]+", t) if w]
    initials = "".join(w[0] for w in words)
    if len(q) >= 2 and initials.startswith(q):
        return 64.0

    pos = 0
    for ch in q:
        pos = t.find(ch, pos)
        if pos < 0:
            return 0.0
        pos += 1
    return max(20.0, 40.0 - (len(t) - len(q)) * 0.08)


class UsageStore:
    """Tiny recency/usage memory so the things you actually use float up."""

    def __init__(self):
        self.path = os.path.join(config.data_dir(), "usage.json")
        self.data: Dict[str, float] = {}
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                self.data = json.load(fh)
        except Exception:
            self.data = {}

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh)
        except Exception:
            pass

    def bump(self, key: str):
        if not key:
            return
        self.data[key] = self.data.get(key, 0) + 1
        self.save()

    def boost(self, key: str) -> float:
        return min(18.0, self.data.get(key, 0) * 4.5)

    def recent(self, limit: int = 6) -> List[str]:
        ordered = sorted(self.data.items(), key=lambda kv: -kv[1])
        return [k for k, _ in ordered[:limit]]


# --------------------------------------------------------------- app index ---

class AppIndex:
    """Installed applications, from Start Menu shortcuts and Store apps."""

    def __init__(self):
        self.apps: List[dict] = []
        self.loaded = False
        self._icon_provider = QFileIconProvider()

    # -- discovery -----------------------------------------------------------

    def load(self):
        if self.loaded:
            return
        self.loaded = True
        apps: Dict[str, dict] = {}

        if IS_WINDOWS:
            for directory in self._start_menu_dirs():
                self._scan_shortcuts(directory, apps)
            for entry in self._store_apps():
                apps.setdefault(entry["name"].lower(), entry)
        elif IS_MACOS:
            self._scan_app_bundles(apps)
        else:
            self._scan_desktop_files(apps)

        self.apps = sorted(apps.values(), key=lambda a: a["name"].lower())
        self._prewarm_icons()

    @staticmethod
    def _start_menu_dirs() -> List[str]:
        dirs = []
        appdata = os.environ.get("APPDATA", "")
        programdata = os.environ.get("PROGRAMDATA", "")
        if appdata:
            dirs.append(os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs"))
        if programdata:
            dirs.append(os.path.join(programdata, "Microsoft", "Windows", "Start Menu", "Programs"))
        return [d for d in dirs if os.path.isdir(d)]

    _SKIP_WORDS = ("uninstall", "readme", "help", "release notes", "license",
                   "website", "documentation", "manual", "changelog", "update")

    def _scan_shortcuts(self, root: str, apps: Dict[str, dict]):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for name in filenames:
                low = name.lower()
                if not (low.endswith(".lnk") or low.endswith(".url")):
                    continue
                stem = os.path.splitext(name)[0]
                if any(word in stem.lower() for word in self._SKIP_WORDS):
                    continue
                path = os.path.join(dirpath, name)
                key = stem.lower()
                if key in apps:
                    continue
                apps[key] = {
                    "name": stem,
                    "path": path,
                    "launch": path,
                    "icon_source": path,
                    "type": "shortcut",
                }

    def _store_apps(self) -> List[dict]:
        """Store/UWP apps never appear as .lnk files; ask Windows once a week."""
        cache = os.path.join(config.data_dir(), "store_apps.json")
        try:
            if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 7 * 86400:
                with open(cache, "r", encoding="utf-8") as fh:
                    return json.load(fh)
        except Exception:
            pass

        entries: List[dict] = []
        try:
            ps = ("Get-StartApps | Select-Object Name,AppID | "
                  "ConvertTo-Json -Compress")
            out = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                capture_output=True, text=True, timeout=25,
                creationflags=CREATE_NO_WINDOW,
            ).stdout.strip()
            if out:
                data = json.loads(out)
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    name = (item.get("Name") or "").strip()
                    app_id = (item.get("AppID") or "").strip()
                    if not name or not app_id:
                        continue
                    entries.append({
                        "name": name,
                        "path": f"shell:AppsFolder\\{app_id}",
                        "launch": f"shell:AppsFolder\\{app_id}",
                        "icon_source": "",
                        "type": "uwp",
                    })
            with open(cache, "w", encoding="utf-8") as fh:
                json.dump(entries, fh)
        except Exception as exc:
            print(f"[circle] store app index skipped: {exc}")
        return entries

    _MAC_APP_DIRS = [
        "/Applications",
        "/System/Applications",
        "/System/Applications/Utilities",
        "/Applications/Utilities",
        os.path.expanduser("~/Applications"),
    ]

    def _scan_app_bundles(self, apps: Dict[str, dict]):
        """A .app bundle is the app: name from the bundle, icon from its icns."""
        for root in self._MAC_APP_DIRS:
            if not os.path.isdir(root):
                continue
            try:
                entries = sorted(os.listdir(root))
            except OSError:
                continue
            for name in entries:
                if not name.endswith(".app"):
                    continue
                bundle = os.path.join(root, name)
                label = os.path.splitext(name)[0]
                key = label.lower()
                if key in apps:
                    continue
                apps[key] = {
                    "name": label,
                    "path": bundle,
                    "launch": bundle,
                    "icon_source": self._bundle_icon(bundle),
                    "type": "bundle",
                }

    @staticmethod
    def _bundle_icon(bundle: str) -> str:
        """Find the .icns Qt can load from inside a bundle."""
        resources = os.path.join(bundle, "Contents", "Resources")
        info = os.path.join(bundle, "Contents", "Info.plist")
        try:
            import plistlib
            with open(info, "rb") as fh:
                declared = plistlib.load(fh).get("CFBundleIconFile") or ""
            if declared:
                if not declared.endswith(".icns"):
                    declared += ".icns"
                candidate = os.path.join(resources, declared)
                if os.path.exists(candidate):
                    return candidate
        except Exception:
            pass
        try:
            for name in os.listdir(resources):
                if name.endswith(".icns"):
                    return os.path.join(resources, name)
        except OSError:
            pass
        return ""

    def _scan_desktop_files(self, apps: Dict[str, dict]):
        """Linux/macOS fallback so the launcher is testable off Windows."""
        roots = ["/usr/share/applications", "/usr/local/share/applications",
                 os.path.expanduser("~/.local/share/applications")]
        for root in roots:
            if not os.path.isdir(root):
                continue
            for name in os.listdir(root):
                if not name.endswith(".desktop"):
                    continue
                path = os.path.join(root, name)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        body = fh.read()
                except Exception:
                    continue
                label = re.search(r"^Name=(.+)$", body, re.M)
                exec_line = re.search(r"^Exec=(.+)$", body, re.M)
                if not label or not exec_line:
                    continue
                apps[label.group(1).strip().lower()] = {
                    "name": label.group(1).strip(),
                    "path": path,
                    "launch": exec_line.group(1).split(" %")[0].strip(),
                    "icon_source": "",
                    "type": "desktop",
                }

    def _prewarm_icons(self):
        """Resolve a few dozen icons now so the first search feels instant."""
        for app in self.apps[:60]:
            self.icon_for(app)

    def icon_for(self, app: dict) -> QIcon:
        cached = app.get("_icon")
        if cached is not None:
            return cached
        icon = QIcon()
        source = app.get("icon_source")
        if source and os.path.exists(source):
            try:
                icon = self._icon_provider.icon(QFileInfo(source))
            except Exception:
                icon = QIcon()
        app["_icon"] = icon
        return icon

    # -- launching -----------------------------------------------------------

    def launch(self, app: dict):
        """Start an app, and raise a readable error if the OS refuses."""
        kind = app.get("type")
        name = app.get("name") or "That app"

        if kind == "uwp":
            if _spawn(["explorer.exe", app["launch"]]):
                return
            raise RuntimeError(f"Windows would not open {name}.")

        if kind == "desktop":
            if _spawn(app["launch"], shell=True):
                return
            raise RuntimeError(f"Could not run the command for {name}.")

        target = app.get("launch") or app.get("path") or ""
        if not target:
            raise RuntimeError(f"{name} has no launch target recorded.")
        if not os.path.exists(target):
            raise RuntimeError(f"{name} is no longer at {target} — it may have been uninstalled.")
        if platform.open_path(target):
            return
        raise RuntimeError(f"Windows would not open {name}.")

    def search(self, query: str, limit: int = 6) -> List[Result]:
        if not query:
            return []
        scored = []
        for app in self.apps:
            score = score_text(query, app["name"])
            if score > 0:
                scored.append((score, app))
        scored.sort(key=lambda pair: -pair[0])

        results = []
        for score, app in scored[:limit]:
            r = Result(
                title=app["name"],
                kind="Apps",
                subtitle="Application",
                icon="app",
                score=score,
                key=f"app:{app['name'].lower()}",
            )
            r.run = (lambda a=app: self.launch(a))
            if app.get("type") != "uwp":
                r.alt_run = (lambda a=app: reveal_path(a["launch"]))
                r.alt_hint = "Reveal"
            r._icon = self.icon_for(app)
            results.append(r)
        return results


# -------------------------------------------------------------- file index ---

class FileIndex:
    """A bounded index of the folders people actually look in."""

    MAX_ENTRIES = 60000
    SKIP_DIRS = {
        "node_modules", ".git", ".svn", "__pycache__", "appdata", "windows",
        "program files", "program files (x86)", "programdata", "$recycle.bin",
        ".venv", "venv", "site-packages", "dist", "build", ".cache",
    }

    def __init__(self):
        self.entries: List[dict] = []
        self.built_at = 0.0
        self.building = False
        self.cache_path = os.path.join(config.data_dir(), "file_index.json")
        self._icon_provider = QFileIconProvider()
        self._icons: Dict[str, QIcon] = {}

    # -- roots ---------------------------------------------------------------

    @staticmethod
    def default_roots() -> List[str]:
        home = os.path.expanduser("~")
        if IS_WINDOWS:
            candidates = ["Desktop", "Documents", "Downloads", "Pictures",
                          "Music", "Videos", "OneDrive"]
        elif IS_MACOS:
            candidates = ["Desktop", "Documents", "Downloads", "Pictures",
                          "Music", "Movies", "Developer"]
        else:
            candidates = ["Desktop", "Documents", "Downloads", "Pictures",
                          "Music", "Videos"]
        roots = [os.path.join(home, c) for c in candidates]
        return [r for r in roots if os.path.isdir(r)]

    def load_cache(self) -> bool:
        try:
            with open(self.cache_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            self.entries = payload.get("entries", [])
            self.built_at = payload.get("built_at", 0)
            return bool(self.entries)
        except Exception:
            return False

    def save_cache(self):
        try:
            with open(self.cache_path, "w", encoding="utf-8") as fh:
                json.dump({"built_at": self.built_at, "entries": self.entries}, fh)
        except Exception as exc:
            print(f"[circle] could not save file index: {exc}")

    def build(self, roots: Optional[List[str]] = None, max_age_days: int = 2) -> int:
        self.building = True
        entries: List[dict] = []
        roots = roots or self.default_roots()
        deadline = time.time() + 45
        try:
            for root in roots:
                for dirpath, dirnames, filenames in os.walk(root):
                    if len(entries) >= self.MAX_ENTRIES or time.time() > deadline:
                        break
                    dirnames[:] = [
                        d for d in dirnames
                        if d.lower() not in self.SKIP_DIRS and not d.startswith(".")
                    ]
                    rel_dir = os.path.relpath(dirpath, root)
                    for name in filenames:
                        if name.startswith("."):
                            continue
                        full = os.path.join(dirpath, name)
                        entries.append({"n": name, "p": full, "d": 0, "r": rel_dir})
                        if len(entries) >= self.MAX_ENTRIES:
                            break
                    for name in dirnames:
                        full = os.path.join(dirpath, name)
                        entries.append({"n": name, "p": full, "d": 1, "r": rel_dir})
            self.entries = entries
            self.built_at = time.time()
            self.save_cache()
        finally:
            self.building = False
        return len(self.entries)

    def is_stale(self, max_age_days: float = 2.0) -> bool:
        return (time.time() - self.built_at) > max_age_days * 86400

    # -- query ---------------------------------------------------------------

    def icon_for(self, path: str, is_dir: bool) -> QIcon:
        key = path if not is_dir else os.path.dirname(path)
        if is_dir:
            return QIcon()
        icon = self._icons.get(key)
        if icon is None:
            try:
                icon = self._icon_provider.icon(QFileInfo(path))
            except Exception:
                icon = QIcon()
            self._icons[key] = icon
        return icon

    def search(self, query: str, limit: int = 6) -> List[Result]:
        if not query or not self.entries:
            return []
        q = query.lower()
        # A path pasted straight in always wins.
        results: List[Result] = []
        if (os.sep in query or (IS_WINDOWS and "/" in query)) and os.path.exists(os.path.expanduser(query)):
            path = os.path.expanduser(query)
            is_dir = os.path.isdir(path)
            results.append(self._make_result(path, os.path.basename(path) or path, is_dir, 999.0))

        scored = []
        for entry in self.entries:
            name = entry["n"].lower()
            if q in name:
                score = score_text(q, name) + (6 if entry["d"] else 0)
            elif q in entry["r"].lower():
                score = 26.0
            else:
                continue
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda pair: -pair[0])

        for score, entry in scored[:limit]:
            results.append(self._make_result(entry["p"], entry["n"], bool(entry["d"]), score))
        return results

    def _make_result(self, path: str, name: str, is_dir: bool, score: float) -> Result:
        parent = os.path.dirname(path)
        home = os.path.expanduser("~")
        if parent.lower().startswith(home.lower()):
            parent = "~" + parent[len(home):]
        r = Result(
            title=name,
            kind="Folders" if is_dir else "Files",
            subtitle=parent or path,
            icon="folder" if is_dir else "file",
            score=score,
            key=f"file:{path.lower()}",
        )
        r.run = (lambda p=path: open_path(p))
        r.alt_run = (lambda p=path: reveal_path(p))
        r.alt_hint = "Reveal"
        if not is_dir:
            r._icon = self.icon_for(path, is_dir)
        return r


class FileIndexer(QThread):
    """Builds the file index off the UI thread."""

    finished_index = Signal(int)

    def __init__(self, index: FileIndex, roots=None, parent=None):
        super().__init__(parent)
        self.index = index
        self.roots = roots

    def run(self):
        try:
            count = self.index.build(self.roots)
        except Exception as exc:
            print(f"[circle] file index failed: {exc}")
            count = 0
        self.finished_index.emit(count)


# ------------------------------------------------------------------ actions ---

def _action(name, keywords, icon, run, subtitle=""):
    r = Result(title=name, kind="Actions", subtitle=subtitle, icon=icon,
               key=f"action:{name.lower()}")
    r.run = run
    return r


def _settings_page(name, uri, icon):
    label = "System Settings" if IS_MACOS else "Windows Settings"
    r = Result(title=name, kind="Settings", subtitle=label, icon=icon,
               key=f"settings:{uri}")
    r.run = (lambda u=uri: platform.open_settings_uri(u))
    return r


WINDOWS_SETTINGS_PAGES = [
    ("Display settings", "ms-settings:display", "display"),
    ("Sound settings", "ms-settings:sound", "sound"),
    ("Bluetooth and devices", "ms-settings:bluetooth", "bluetooth"),
    ("Wi-Fi settings", "ms-settings:network-wifi", "wifi"),
    ("Network and internet", "ms-settings:network", "globe"),
    ("Apps and features", "ms-settings:appsfeatures", "app"),
    ("Windows Update", "ms-settings:windowsupdate", "update"),
    ("Personalisation", "ms-settings:personalization", "star"),
    ("Mouse settings", "ms-settings:mousetouchpad", "mouse"),
    ("Keyboard settings", "ms-settings:keyboard", "keyboard"),
    ("Privacy", "ms-settings:privacy", "privacy"),
    ("Power and battery", "ms-settings:batterysaver", "battery"),
    ("Accounts", "ms-settings:yourinfo", "user"),
    ("Date and time", "ms-settings:dateandtime", "clock"),
    ("Default apps", "ms-settings:defaultapps", "store"),
    ("Storage", "ms-settings:storagesense", "sheet"),
    ("Clipboard", "ms-settings:clipboard", "copy"),
    ("Focus assist", "ms-settings:quiethours", "sleep"),
    ("Multitasking", "ms-settings:multitasking", "window"),
    ("Windows Security", "windowsdefender:", "lock"),
]

MACOS_SETTINGS_PAGES = [
    ("Displays", "x-apple.systempreferences:com.apple.Displays-Settings.extension", "display"),
    ("Sound", "x-apple.systempreferences:com.apple.Sound-Settings.extension", "sound"),
    ("Bluetooth", "x-apple.systempreferences:com.apple.Bluetooth-Settings.extension", "bluetooth"),
    ("Wi-Fi", "x-apple.systempreferences:com.apple.wifi-settings-extension", "wifi"),
    ("Network", "x-apple.systempreferences:com.apple.Network-Settings.extension", "globe"),
    ("Appearance", "x-apple.systempreferences:com.apple.Appearance-Settings.extension", "star"),
    ("Desktop and Dock", "x-apple.systempreferences:com.apple.Desktop-Settings.extension", "window"),
    ("Wallpaper", "x-apple.systempreferences:com.apple.Wallpaper-Settings.extension", "image"),
    ("Notifications", "x-apple.systempreferences:com.apple.Notifications-Settings.extension", "mail"),
    ("Focus", "x-apple.systempreferences:com.apple.Focus-Settings.extension", "sleep"),
    ("Keyboard", "x-apple.systempreferences:com.apple.Keyboard-Settings.extension", "keyboard"),
    ("Trackpad", "x-apple.systempreferences:com.apple.Trackpad-Settings.extension", "mouse"),
    ("Mouse", "x-apple.systempreferences:com.apple.Mouse-Settings.extension", "mouse"),
    ("Accessibility", "x-apple.systempreferences:com.apple.Accessibility-Settings.extension", "user"),
    ("Privacy and Security", "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension", "privacy"),
    ("Battery", "x-apple.systempreferences:com.apple.Battery-Settings.extension", "battery"),
    ("Users and Groups", "x-apple.systempreferences:com.apple.Users-Groups-Settings.extension", "user"),
    ("Software Update", "x-apple.systempreferences:com.apple.Software-Update-Settings.extension", "update"),
    ("Date and Time", "x-apple.systempreferences:com.apple.Date-Time-Settings.extension", "clock"),
    ("Storage", "x-apple.systempreferences:com.apple.settings.Storage", "sheet"),
]

SETTINGS_PAGES = MACOS_SETTINGS_PAGES if IS_MACOS else WINDOWS_SETTINGS_PAGES


def build_actions() -> List[Result]:
    """The system actions worth a keystroke, per platform."""
    if IS_MACOS:
        actions = [
            _action("Lock the screen", "lock secure", "lock", platform.lock_screen),
            _action("Sleep", "suspend standby", "sleep", platform.sleep_machine),
            _action("Take a screenshot", "capture screen grab snip", "camera",
                    platform.screenshot),
            _action("Open Activity Monitor", "processes cpu memory task manager",
                    "display", platform.open_task_manager),
            _action("Open Terminal", "shell command line console", "terminal",
                    platform.open_terminal),
            _action("Open Finder", "files folders explorer", "folder",
                    lambda: platform.open_path(os.path.expanduser("~"))),
            _action("Open TextEdit", "notes editor text", "text",
                    lambda: platform.open_path("/System/Applications/TextEdit.app")),
            _action("Open Calculator", "maths numbers calc", "calc",
                    lambda: platform.open_path("/System/Applications/Calculator.app")),
            _action("Show the desktop", "reveal desktop minimise", "window",
                    platform.show_desktop),
            _action("Empty the Trash", "trash delete bin clean", "bin",
                    platform.empty_trash),
            _action("Sign out", "log out logoff account", "user", platform.sign_out),
        ]
    else:
        actions = [
            _action("Lock the screen", "lock secure workstation", "lock",
                    lambda: _spawn(["rundll32.exe", "user32.dll,LockWorkStation"])
                    if IS_WINDOWS else None),
            _action("Sleep", "suspend standby power", "sleep",
                    lambda: _spawn(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
                    if IS_WINDOWS else None),
            _action("Take a screenshot", "capture screen grab", "camera",
                    lambda: _spawn(["cmd", "/c", "start", "", "ms-screenclip:"])
                    if IS_WINDOWS else None),
            _action("Open Task Manager", "processes cpu memory", "display",
                    lambda: _spawn(["taskmgr.exe"])),
            _action("Open Terminal", "command prompt cmd shell powershell", "terminal",
                    lambda: _spawn(["wt.exe"]) if IS_WINDOWS else _spawn(["x-terminal-emulator"])),
            _action("Open File Explorer", "files folders explorer", "folder",
                    lambda: _spawn(["explorer.exe"]) if IS_WINDOWS else open_path(os.path.expanduser("~"))),
            _action("Open Notepad", "text editor notes", "text",
                    lambda: _spawn(["notepad.exe"])),
            _action("Open Calculator", "math numbers", "calc",
                    lambda: _spawn(["calc.exe"])),
            _action("Show the desktop", "minimise everything", "window",
                    lambda: _spawn(["cmd", "/c", "start", "", "shell:AppsFolder\\Microsoft.Windows.Explorer"])
                    if IS_WINDOWS else None),
            _action("Empty the Recycle Bin", "trash delete bin clean", "bin",
                    lambda: _spawn(["powershell", "-NoProfile", "-Command",
                                    "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"])),
            _action("Sign out", "log off logoff account", "user",
                    lambda: _spawn(["shutdown", "/l"]) if IS_WINDOWS else None),
        ]
    actions += [_settings_page(n, u, i) for n, u, i in SETTINGS_PAGES]
    return [a for a in actions if a.run is not None]


# ---------------------------------------------------------------- calculator ---

_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Add, ast.Sub,
    ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv, ast.USub, ast.UAdd,
    ast.Call, ast.Name, ast.Load, ast.Tuple,
)
_ALLOWED_FUNCS = {
    "sqrt": math.sqrt, "abs": abs, "round": round, "min": min, "max": max,
    "sin": math.sin, "cos": math.cos, "tan": math.tan, "log": math.log,
    "log10": math.log10, "exp": math.exp, "floor": math.floor, "ceil": math.ceil,
}


def _format_number(value: float) -> str:
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
        return f"{int(value):,}"
    if abs(value) >= 1e15 or (value != 0 and abs(value) < 1e-6):
        return f"{value:.6e}"
    text = f"{value:,.6f}".rstrip("0").rstrip(".")
    return text


def try_calculate(query: str) -> Optional[Result]:
    raw = query.strip().replace("×", "*").replace("÷", "/").replace("−", "-")
    raw = raw.replace("^", "**")

    percent_of = re.fullmatch(r"([\d.]+)\s*%\s*(?:of|off)\s*([\d.]+)", raw, re.I)
    if percent_of:
        value = float(percent_of.group(1)) / 100.0 * float(percent_of.group(2))
        return _calc_result(f"{percent_of.group(1)}% of {percent_of.group(2)}", value)

    if not re.fullmatch(r"[\d\s.+\-*/%()eE,]+", raw):
        return None
    if not re.search(r"\d", raw) or not re.search(r"[+\-*/%]", raw):
        return None
    expr = raw.replace(",", "")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            return None
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCS:
                return None
    try:
        value = eval(compile(tree, "<circle-calc>", "eval"),  # noqa: S307 - whitelisted
                     {"__builtins__": {}}, _ALLOWED_FUNCS)
    except Exception:
        return None
    if isinstance(value, complex):
        return None
    return _calc_result(expr, float(value))


def _calc_result(expression: str, value: float) -> Result:
    formatted = _format_number(value)
    r = Result(
        title=formatted,
        kind="Calculator",
        subtitle=f"{expression}  ·  Enter to copy",
        icon="calc",
        score=1000.0,
        key=f"calc:{expression}",
    )

    def copy_value():
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(formatted)

    r.run = copy_value
    return r


# --------------------------------------------------------------------- web ---

WEB_SHORTCUTS = {
    "g": "https://www.google.com/search?q={q}",
    "yt": "https://www.youtube.com/results?search_query={q}",
    "gh": "https://github.com/search?q={q}",
    "w": "https://en.wikipedia.org/w/index.php?search={q}",
    "npm": "https://www.npmjs.com/search?q={q}",
    "maps": "https://www.google.com/maps/search/{q}",
}


def web_results(query: str, engine: str) -> List[Result]:
    q = query.strip()
    if not q:
        return []
    results: List[Result] = []

    if re.match(r"^https?://\S+$", q) or re.match(r"^[\w-]+(\.[\w-]+)+/?\S*$", q) and " " not in q:
        url = q if q.startswith("http") else "https://" + q
        r = Result(title=f"Open {url}", kind="Web", subtitle="Website", icon="globe",
                   score=60.0, key=f"url:{url}")
        r.run = (lambda u=url: open_url(u))
        results.append(r)

    shortcut = re.match(r"^@(\w+)\s+(.+)$", q)
    if shortcut and shortcut.group(1) in WEB_SHORTCUTS:
        term = shortcut.group(2)
        template = WEB_SHORTCUTS[shortcut.group(1)]
        url = template.format(q=urllib.parse.quote_plus(term))
        r = Result(title=f"Search {shortcut.group(1)} for “{term}”", kind="Web",
                   subtitle=url.split("//")[1].split("/")[0], icon="search",
                   score=58.0, key=f"web:{url}")
        r.run = (lambda u=url: open_url(u))
        results.append(r)

    url = engine.format(q=urllib.parse.quote_plus(q))
    r = Result(title=f"Search the web for “{q}”", kind="Web",
               subtitle="Google", icon="search", score=30.0, key=f"web:{url}")
    r.run = (lambda u=url: open_url(u))
    results.append(r)
    return results


# ------------------------------------------------------------------ windows ---

def list_open_windows() -> List[dict]:
    """Top-level windows you could switch to."""
    return platform.list_windows()


def focus_window(handle):
    platform.activate_window(handle)


# --------------------------------------------------------------- the engine ---

class SearchEngine:
    """Owns the indexes and turns a query into a grouped, ranked list."""

    def __init__(self):
        self.usage = UsageStore()
        self.apps = AppIndex()
        self.files = FileIndex()
        self.actions = build_actions()
        self._windows_cache: List[dict] = []
        self._windows_at = 0.0

    # -- lifecycle -----------------------------------------------------------

    def warm(self):
        self.apps.load()
        if self.files.load_cache() is None:
            pass

    def start_file_index(self, force=False) -> Optional[FileIndexer]:
        if self.files.building:
            return None
        if not force and self.files.entries and not self.files.is_stale():
            return None
        thread = FileIndexer(self.files)
        thread.start()
        return thread

    # -- query ---------------------------------------------------------------

    def windows(self) -> List[dict]:
        now = time.time()
        if now - self._windows_at > 3.0:
            self._windows_cache = list_open_windows()
            self._windows_at = now
        return self._windows_cache

    def search(self, query: str, limit_per_group: int = 5, max_groups: int = 5) -> List[Result]:
        query = query.strip()
        results: List[Result] = []

        if not query:
            return self.suggestions(limit_per_group)

        calc = try_calculate(query)
        if calc:
            results.append(calc)

        for win in self.windows():
            title = win.get("title") or win.get("app") or ""
            score = score_text(query, title)
            if score > 0:
                subtitle = win.get("app") or "Switch to window"
                r = Result(title=title, kind="Windows", subtitle=subtitle,
                           icon="window", score=score,
                           key=f"win:{title.lower()}")
                r.run = (lambda h=win["handle"]: platform.activate_window(h))
                results.append(r)

        results.extend(self.apps.search(query, limit_per_group))
        results.extend(self.files.search(query, limit_per_group))

        for action in self.actions:
            score = score_text(query, action.title)
            if score > 0:
                clone = Result(**{**action.__dict__})
                clone.score = score
                results.append(clone)

        results.extend(web_results(query, config.get_web_engine()))

        return self._group(results, limit_per_group, max_groups)

    def _group(self, results: List[Result], per_group: int, max_groups: int) -> List[Result]:
        buckets: Dict[str, List[Result]] = {}
        for r in results:
            r.score += self.usage.boost(r.key)
            buckets.setdefault(r.group, []).append(r)

        ordered = []
        for group, items in buckets.items():
            items.sort(key=lambda r: -r.score)
            ordered.append((items[0].score, group, items[:per_group]))
        ordered.sort(key=lambda trio: (-trio[0], _group_rank(trio[1])))

        final: List[Result] = []
        for _, _group_name, items in ordered[:max_groups]:
            final.extend(items)
        return final

    def suggestions(self, limit: int = 6) -> List[Result]:
        """What an empty query shows: your recents, then a way in."""
        out: List[Result] = []
        recent_keys = self.usage.recent(limit)
        lookup: Dict[str, Result] = {}
        for action in self.actions:
            lookup[action.key] = action
        for app in self.apps.apps:
            key = f"app:{app['name'].lower()}"
            if key in recent_keys:
                r = Result(title=app["name"], kind="Recent", subtitle="Application",
                           icon="app", key=key)
                r.run = (lambda a=app: self.apps.launch(a))
                r._icon = self.apps.icon_for(app)
                lookup[key] = r
        for key in recent_keys:
            if key in lookup:
                out.append(lookup[key])

        seen = {r.key for r in out}
        for action in self.actions:
            if len(out) >= limit:
                break
            if action.key in seen or action.group != "Actions":
                continue
            clone = Result(**action.__dict__)
            clone.kind = "Suggested"
            out.append(clone)
            seen.add(action.key)
        return out[:limit]

    def record_use(self, result: Result):
        self.usage.bump(result.key)


def _group_rank(name: str) -> int:
    try:
        return GROUP_ORDER.index(name)
    except ValueError:
        return len(GROUP_ORDER)
