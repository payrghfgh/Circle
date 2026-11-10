import threading
import time
from PySide6.QtCore import QObject, Signal
from pynput import keyboard, mouse

class HotkeyManager(QObject):
    triggered = Signal()

    def __init__(self, hotkey_str="<ctrl>+<space>", double_space_dot=False):
        super().__init__()
        self.hotkey_str = hotkey_str
        self.double_space_dot = double_space_dot
        self.listener = None
        self.mouse_listener = None
        self.double_space_listener = None
        self.is_running = False
        
        # Tracking double space
        self.last_space_time = 0
        self.keyboard_controller = keyboard.Controller()

    def update_settings(self, new_hotkey_str, double_space_dot=False):
        self.stop()
        self.hotkey_str = new_hotkey_str
        self.double_space_dot = double_space_dot
        self.start()

    def update_hotkey(self, new_hotkey_str):
        self.update_settings(new_hotkey_str, self.double_space_dot)

    def _on_trigger(self):
        self.triggered.emit()

    def start(self):
        if self.is_running:
            return
        self.is_running = True

        if self.hotkey_str.lower() in ["middle_click", "middle click", "button.middle"]:
            self._start_mouse_listener()
        else:
            self._start_keyboard_listener()

        if self.double_space_dot:
            self._start_double_space_listener()

    def _start_keyboard_listener(self):
        try:
            # Format hotkey string for pynput
            formatted_hotkey = self.hotkey_str
            if "ctrl" in formatted_hotkey.lower() and "<ctrl>" not in formatted_hotkey:
                formatted_hotkey = formatted_hotkey.lower().replace("ctrl", "<ctrl>")
            if "alt" in formatted_hotkey.lower() and "<alt>" not in formatted_hotkey:
                formatted_hotkey = formatted_hotkey.lower().replace("alt", "<alt>")
            if "shift" in formatted_hotkey.lower() and "<shift>" not in formatted_hotkey:
                formatted_hotkey = formatted_hotkey.lower().replace("shift", "<shift>")
            if "space" in formatted_hotkey.lower() and "<space>" not in formatted_hotkey:
                formatted_hotkey = formatted_hotkey.lower().replace("space", "<space>")

            hotkey_dict = {
                formatted_hotkey: self._on_trigger
            }

            self.listener = keyboard.GlobalHotKeys(hotkey_dict)
            self.listener.start()
        except Exception as e:
            print(f"Error starting keyboard hotkey listener '{self.hotkey_str}': {e}")
            try:
                self.listener = keyboard.GlobalHotKeys({"<ctrl>+<space>": self._on_trigger})
                self.listener.start()
            except Exception as ex:
                print(f"Fallback hotkey listener failed: {ex}")

    def _start_double_space_listener(self):
        def on_press(key):
            if key == keyboard.Key.space:
                now = time.time()
                if now - self.last_space_time < 0.4:  # Within 400ms interval
                    self.last_space_time = 0
                    # Double space pressed! Remove 2 spaces and send '. '
                    def replace_spaces():
                        try:
                            # Send 2 backspaces to clear the 2 typed spaces
                            self.keyboard_controller.press(keyboard.Key.backspace)
                            self.keyboard_controller.release(keyboard.Key.backspace)
                            self.keyboard_controller.press(keyboard.Key.backspace)
                            self.keyboard_controller.release(keyboard.Key.backspace)
                            # Type ". "
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
                self._on_trigger()

        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()

    def stop(self):
        self.is_running = False
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None

        if self.mouse_listener:
            try:
                self.mouse_listener.stop()
            except Exception:
                pass
            self.mouse_listener = None

        if self.double_space_listener:
            try:
                self.double_space_listener.stop()
            except Exception:
                pass
            self.double_space_listener = None

