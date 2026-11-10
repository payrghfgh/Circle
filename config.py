import json
import os
import sys

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
FROZEN = bool(getattr(sys, "frozen", False))

DEFAULT_WEB_ENGINE = "https://www.google.com/search?q={q}"

# Ctrl+Space is taken by input-source switching on macOS, and Cmd+Space by
# Spotlight, so the wheel defaults to Ctrl+Option+Space there.
DEFAULT_WHEEL_HOTKEY = "<ctrl>+<alt>+<space>" if IS_MACOS else "<ctrl>+<space>"
DEFAULT_SEARCH_HOTKEY = "<alt>+<space>"

DEFAULT_CONFIG = {
    "hotkey": DEFAULT_WHEEL_HOTKEY,
    "search_hotkey": DEFAULT_SEARCH_HOTKEY,
    "autostart": True,
    "double_space_dot": False,
    "trigger_mode": "toggle",
    "search": {
        "index_files": True,
        "max_results": 5,
        "web_engine": DEFAULT_WEB_ENGINE,
        "extra_index_roots": [],
    },
    "theme": {
        "bg_color": "#101014",
        "accent_color": "#8AB4FF",
        "hover_color": "#20202A",
        "text_color": "#EDEDF2",
        "radius": 140,
        "inner_radius": 45,
    },
    "slots": [
        {"id": 1, "name": "Search", "icon": "", "icon_name": "search",
         "action_type": "search", "action_detail": "", "color": "#8AB4FF"},
        {"id": 2, "name": "Volume Up", "icon": "", "icon_name": "sound",
         "action_type": "volume", "action_detail": "up", "color": "#8BE0A4"},
        {"id": 3, "name": "Open Browser", "icon": "", "icon_name": "globe",
         "action_type": "open_url", "action_detail": "https://www.google.com",
         "color": "#74C7EC"},
        {"id": 4, "name": "Screenshot", "icon": "", "icon_name": "camera",
         "action_type": "system", "action_detail": "screenshot", "color": "#FAB387"},
        {"id": 5, "name": "Volume Down", "icon": "", "icon_name": "sound",
         "action_type": "volume", "action_detail": "down", "color": "#FF8095"},
        {"id": 6, "name": "Notepad", "icon": "", "icon_name": "text",
         "action_type": "open_app", "action_detail": "notepad.exe", "color": "#CBA6F7"},
        {"id": 7, "name": "Mute Audio", "icon": "", "icon_name": "sound",
         "action_type": "volume", "action_detail": "mute", "color": "#F9E2AF"},
    ],
}

_runtime = {}


def data_dir():
    """Where Circle keeps its own caches and usage history."""
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or BASE_DIR
    elif IS_MACOS:
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.join(
            os.path.expanduser("~"), ".cache"
        )
    path = os.path.join(base, "Circle")
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        return BASE_DIR
    return path


def _config_path():
    """Installed builds keep the user's config in their own profile, not in
    Program Files where an upgrade would overwrite it."""
    if FROZEN:
        return os.path.join(data_dir(), "config.json")
    return os.path.join(BASE_DIR, "config.json")


def _merge_defaults(data):
    for key, val in DEFAULT_CONFIG.items():
        if key not in data:
            data[key] = val
        elif isinstance(val, dict) and isinstance(data.get(key), dict):
            for sub_key, sub_val in val.items():
                data[key].setdefault(sub_key, sub_val)
    return data


def load_config():
    config_file = _config_path()
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = _merge_defaults(json.load(f))
                _runtime.clear()
                _runtime.update(data)
                return data
        except Exception as e:
            print(f"Error loading config, resetting to default: {e}")
            return dict(DEFAULT_CONFIG)
    else:
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)


def save_config(config_data):
    try:
        with open(_config_path(), "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        _runtime.clear()
        _runtime.update(config_data)
    except Exception as e:
        print(f"Error saving config: {e}")


def get_search_settings():
    search = _runtime.get("search")
    if not isinstance(search, dict):
        search = dict(DEFAULT_CONFIG["search"])
    return search


def get_web_engine():
    return get_search_settings().get("web_engine") or DEFAULT_WEB_ENGINE


def index_roots():
    """User folders, plus anything extra the user added in settings."""
    from search_providers import FileIndex  # local import: avoids a cycle
    roots = list(FileIndex.default_roots())
    for extra in get_search_settings().get("extra_index_roots", []) or []:
        if extra and os.path.isdir(extra) and extra not in roots:
            roots.append(extra)
    return roots
