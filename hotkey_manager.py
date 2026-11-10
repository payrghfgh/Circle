import threading
import time

from pynput import keyboard, mouse
from PySide6.QtCore import QObject, Signal


def normalize_hotkey(hotkey_str: str) -> str:
    """Turn loosely typed shortcuts into pynput's '<ctrl>+<space>' form."""
    text = (hotkey_str or "").strip().lower()
    if not text:
        return "<ctrl>+<space>"
    for token in ("ctrl", "alt", "shift", "cmd", "space"):
        if token in text and f"<{token}>" not in text:
            text = text.replace(token, f"<{token}>")
    text = text.replace("<control>", "<ctrl>")
    return text


class HotkeyManager(QObject):
    """Two global shortcuts: the wheel, and Search.

    They are separate listeners so one of them can be a mouse button without
    taking the keyboard shortcut down with it.
    """

    triggered = Signal()          # radial wheel
    search_triggered = Signal()   # Spotlight panel

    def __init__(self, hotkey_str="<ctrl>+<space>", double_space_dot=False,
                 search_hotkey="<alt>+<space>"):
        super().__init__()
        self.hotkey_str = hotkey_str
        self.search_hotkey = search_hotkey
        self.double_space_dot = double_space_dot
        self.wheel_listener = None
        self.search_listener = None
        self.mouse_listener = None
        self.double_space_listener = None
        self.is_running = False

        self.last_space_time = 0
        self.keyboard_controller = keyboard.Controller()

    # ------------------------------------------------------------------ api --

    def update_settings(self, new_hotkey_str, double_space_dot=False, search_hotkey=None):
        self.stop()
        self.hotkey_str = new_hotkey_str
        self.double_space_dot = double_space_dot
        if search_hotkey is not None:
            self.search_hotkey = search_hotkey
        self.start()

    def update_hotkey(self, new_hotkey_str):
        self.update_settings(new_hotkey_str, self.double_space_dot)

    def start(self):
        if self.is_running:
            return
        self.is_running = True

        if self.hotkey_str.lower() in ("middle_click", "middle click", "button.middle"):
            self._start_mouse_listener()
        else:
            self.wheel_listener = self._bind(self.hotkey_str, self.triggered.emit)

        if self.search_hotkey and self.search_hotkey.lower() != self.hotkey_str.lower():
            self.search_listener = self._bind(self.search_hotkey, self.search_triggered.emit)

        if self.double_space_dot:
            self._start_double_space_listener()

    def stop(self):
        self.is_running = False
        for attr in ("wheel_listener", "search_listener", "mouse_listener",
                     "double_space_listener"):
            listener = getattr(self, attr, None)
            if listener is not None:
                try:
                    listener.stop()
                except Exception:
                    pass
                setattr(self, attr, None)

    # ------------------------------------------------------------- internals --

    def _bind(self, hotkey: str, callback):
        try:
            listener = keyboard.GlobalHotKeys({normalize_hotkey(hotkey): callback})
            listener.start()
            return listener
        except Exception as exc:
            print(f"Error binding hotkey '{hotkey}': {exc}")
            return None

    def _start_double_space_listener(self):
        def on_press(key):
            if key == keyboard.Key.space:
                now = time.time()
                if now - self.last_space_time < 0.4:
                    self.last_space_time = 0

                    def replace_spaces():
                        try:
                            for _ in range(2):
                                self.keyboard_controller.press(keyboard.Key.backspace)
                                self.keyboard_controller.release(keyboard.Key.backspace)
                            self.keyboard_controller.type(". ")
                        except Exception as err:
                            print(f"Error executing double space replacement: {err}")

                    threading.Thread(target=replace_spaces, daemon=True).start()
                else:
                    self.last_space_time = now
            else:
                self.last_space_time = 0

        try:
            self.double_space_listener = keyboard.Listener(on_press=on_press)
            self.double_space_listener.start()
        except Exception as e:
            print(f"Error starting double space listener: {e}")

    def _start_mouse_listener(self):
        def on_click(x, y, button, pressed):
            if pressed and button == mouse.Button.middle:
                self.triggered.emit()

        try:
            self.mouse_listener = mouse.Listener(on_click=on_click)
            self.mouse_listener.start()
        except Exception as e:
            print(f"Error starting mouse listener: {e}")
