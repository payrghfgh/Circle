import json
import os

import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "hotkey": "<ctrl>+<space>",
    "autostart": True,
    "double_space_dot": False,
    "trigger_mode": "toggle",
    "theme": {
        "bg_color": "#1E1E2E",
        "accent_color": "#89B4FA",
        "hover_color": "#313244",
        "text_color": "#CDD6F4",
        "radius": 140,
        "inner_radius": 45
    },
    "slots": [
        {
            "id": 1,
            "name": "Volume Up",
            "icon": "🔊",
            "action_type": "volume",
            "action_detail": "up",
            "color": "#89B4FA"
        },
        {
            "id": 2,
            "name": "Open Browser",
            "icon": "🌐",
            "action_type": "open_url",
            "action_detail": "https://www.google.com",
            "color": "#A6E3A1"
        },
        {
            "id": 3,
            "name": "Screenshot",
            "icon": "📸",
            "action_type": "system",
            "action_detail": "screenshot",
            "color": "#FAB387"
        },
        {
            "id": 4,
            "name": "Volume Down",
            "icon": "🔉",
            "action_type": "volume",
            "action_detail": "down",
            "color": "#F38BA8"
        },
        {
            "id": 5,
            "name": "Notepad",
            "icon": "📝",
            "action_type": "open_app",
            "action_detail": "notepad.exe",
            "color": "#CBA6F7"
        },
        {
            "id": 6,
            "name": "Mute Audio",
            "icon": "🔇",
            "action_type": "volume",
            "action_detail": "mute",
            "color": "#F9E2AF"
        }
    ]
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for key, val in DEFAULT_CONFIG.items():
                    if key not in data:
                        data[key] = val
                return data
        except Exception as e:
            print(f"Error loading config, resetting to default: {e}")
            return DEFAULT_CONFIG.copy()
    else:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

def save_config(config_data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")
