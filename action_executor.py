import os
import sys
import subprocess
import webbrowser
import ctypes
import time
import winreg
from PIL import ImageGrab
from pynput.keyboard import Controller, Key

keyboard_controller = Controller()

# Global window handles registered from main app
_app_search_window = None
_voice_typing_hud = None
_window_switcher_window = None

def register_special_windows(app_search_win, voice_hud, window_switcher_win=None):
    global _app_search_window, _voice_typing_hud, _window_switcher_window
    _app_search_window = app_search_win
    _voice_typing_hud = voice_hud
    _window_switcher_window = window_switcher_win

VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF

def _send_win_key(vk_code):
    try:
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
    except Exception as e:
        print(f"Keybd event error: {e}")

_cached_endpoint_volume = None

def _get_volume_object():
    global _cached_endpoint_volume
    if _cached_endpoint_volume is not None:
        return _cached_endpoint_volume
    try:
        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        if hasattr(speakers, "EndpointVolume"):
            _cached_endpoint_volume = speakers.EndpointVolume
            return _cached_endpoint_volume
        elif hasattr(speakers, "Activate"):
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import IAudioEndpointVolume
            interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            _cached_endpoint_volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
            return _cached_endpoint_volume
    except Exception as e:
        print(f"Error initializing volume object: {e}")
    return None

def get_system_volume():
    vol_obj = _get_volume_object()
    if vol_obj:
        try:
            return int(round(vol_obj.GetMasterVolumeLevelScalar() * 100))
        except Exception:
            global _cached_endpoint_volume
            _cached_endpoint_volume = None
    return 50

def set_system_volume_percent(percent):
    target_pct = max(0, min(100, int(round(percent))))
    vol_obj = _get_volume_object()
    if vol_obj:
        try:
            target_scalar = target_pct / 100.0
            vol_obj.SetMasterVolumeLevelScalar(target_scalar, None)
            return target_pct
        except Exception:
            global _cached_endpoint_volume
            _cached_endpoint_volume = None
    return target_pct

def set_system_volume_change(change_percent):
    current_vol = get_system_volume()
    new_vol = max(0, min(100, current_vol + change_percent))
    set_system_volume_percent(new_vol)
    
    if change_percent > 0:
        _send_win_key(VK_VOLUME_UP)
    elif change_percent < 0:
        _send_win_key(VK_VOLUME_DOWN)
        
    return new_vol

def toggle_system_mute():
    vol_obj = _get_volume_object()
    if vol_obj:
        try:
            is_muted = vol_obj.GetMute()
            vol_obj.SetMute(not is_muted, None)
            _send_win_key(VK_VOLUME_MUTE)
            return not is_muted
        except Exception:
            global _cached_endpoint_volume
            _cached_endpoint_volume = None
    _send_win_key(VK_VOLUME_MUTE)
    return None

# Startup Autostart Registry Helper
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "CircleWheelMenu"

def set_autostart(enable=True):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_ALL_ACCESS)
        if enable:
            if getattr(sys, 'frozen', False):
                cmd = f'"{sys.executable}"'
            else:
                script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_circle.bat")
                cmd = f'"{script_path}"'
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Error setting autostart: {e}")
        return False

def get_autostart():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False

def execute_slot_action(slot_data):
    """Execute action based on slot settings."""
    action_type = slot_data.get("action_type", "")
    detail = slot_data.get("action_detail", "").strip()

    try:
        if action_type == "window_switcher":
            if _window_switcher_window:
                _window_switcher_window.show_centered()

        elif action_type == "app_search":
            if _app_search_window:
                _app_search_window.show_centered()

        elif action_type == "voice_to_text":
            if _voice_typing_hud:
                _voice_typing_hud.trigger_voice_dictation()
            else:
                keyboard_controller.press(Key.cmd)
                keyboard_controller.press('h')
                keyboard_controller.release('h')
                keyboard_controller.release(Key.cmd)

        elif action_type == "volume":
            if detail == "up":
                set_system_volume_change(2)
            elif detail == "down":
                set_system_volume_change(-2)
            elif detail == "mute":
                toggle_system_mute()

        elif action_type == "media":
            if detail == "playpause":
                keyboard_controller.tap(Key.media_play_pause)
            elif detail == "next":
                keyboard_controller.tap(Key.media_next)
            elif detail == "prev":
                keyboard_controller.tap(Key.media_previous)

        elif action_type == "open_app":
            if detail:
                if os.path.exists(detail):
                    os.startfile(detail)
                else:
                    subprocess.Popen(detail, shell=True)

        elif action_type == "open_url":
            if detail:
                if not (detail.startswith("http://") or detail.startswith("https://")):
                    detail = "https://" + detail
                webbrowser.open(detail)

        elif action_type == "keyboard":
            keys = [k.strip().lower() for k in detail.split("+")]
            key_map = {
                "ctrl": Key.ctrl,
                "alt": Key.alt,
                "shift": Key.shift,
                "win": Key.cmd,
                "tab": Key.tab,
                "enter": Key.enter,
                "space": Key.space,
                "backspace": Key.backspace,
                "esc": Key.esc,
                "playpause": Key.media_play_pause,
                "next": Key.media_next,
                "previous": Key.media_previous
            }
            
            pynput_keys = []
            for k in keys:
                if k in key_map:
                    pynput_keys.append(key_map[k])
                elif len(k) == 1:
                    pynput_keys.append(k)
                    
            for k in pynput_keys:
                keyboard_controller.press(k)
            for k in reversed(pynput_keys):
                keyboard_controller.release(k)

        elif action_type == "system":
            if detail == "screenshot":
                time.sleep(0.2)
                screenshot = ImageGrab.grab()
                pictures_dir = os.path.join(os.path.expanduser("~"), "Pictures")
                os.makedirs(pictures_dir, exist_ok=True)
                save_path = os.path.join(pictures_dir, f"Circle_Screenshot_{int(time.time())}.png")
                screenshot.save(save_path)
                os.startfile(pictures_dir)
            elif detail == "snip":
                keyboard_controller.press(Key.cmd)
                keyboard_controller.press(Key.shift)
                keyboard_controller.press('s')
                keyboard_controller.release('s')
                keyboard_controller.release(Key.shift)
                keyboard_controller.release(Key.cmd)
            elif detail == "lock":
                ctypes.windll.user32.LockWorkStation()
            elif detail == "taskmgr":
                subprocess.Popen("taskmgr.exe")
            elif detail == "calc":
                subprocess.Popen("calc.exe")
            elif detail == "notepad":
                subprocess.Popen("notepad.exe")
            elif detail == "explorer":
                subprocess.Popen("explorer.exe")
            elif detail == "settings":
                subprocess.Popen("start ms-settings:", shell=True)
            elif detail == "show_desktop":
                keyboard_controller.press(Key.cmd)
                keyboard_controller.press('d')
                keyboard_controller.release('d')
                keyboard_controller.release(Key.cmd)

        elif action_type == "shell":
            if detail:
                subprocess.Popen(detail, shell=True)

        elif action_type == "web_search":
            query = detail if detail else "Python"
            webbrowser.open(f"https://www.google.com/search?q={query}")

    except Exception as e:
        print(f"Error executing slot action {action_type} - {detail}: {e}")
