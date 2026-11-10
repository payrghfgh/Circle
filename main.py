import sys
import os
from PySide6.QtCore import Qt, QObject, Signal, QThread
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

from config import load_config, save_config
from wheel_overlay import WheelOverlay
from settings_gui import SettingsWindow
from hotkey_manager import HotkeyManager
from action_executor import set_autostart, register_special_windows
from app_search import AppSearchWindow
from voice_typing import VoiceTypingHUD
from window_switcher import WindowSwitcherWindow

def create_circle_tray_icon():
    """Generates a sleek radial circle icon for system tray."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Outer circle
    painter.setBrush(QColor(30, 30, 46))
    painter.setPen(QColor(137, 180, 250))
    painter.drawEllipse(4, 4, 56, 56)

    # Inner core
    painter.setBrush(QColor(137, 180, 250))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(22, 22, 20, 20)

    painter.end()
    return QIcon(pixmap)

class CircleApp(QObject):
    trigger_overlay_signal = Signal()

    def __init__(self):
        super().__init__()
        self.config_data = load_config()

        # Ensure autostart setting is registered in Windows Startup
        if self.config_data.get("autostart", True):
            set_autostart(True)

        # Initialize Special Feature Windows
        self.app_search_window = AppSearchWindow()
        self.voice_typing_hud = VoiceTypingHUD()
        self.window_switcher_window = WindowSwitcherWindow()
        register_special_windows(self.app_search_window, self.voice_typing_hud, self.window_switcher_window)

        # Initialize Overlay Window
        self.overlay = WheelOverlay(self.config_data)

        # Initialize Settings Window
        self.settings_window = SettingsWindow(self.config_data)

        # Initialize Hotkey Manager
        self.hotkey_manager = HotkeyManager(
            self.config_data.get("hotkey", "<ctrl>+<space>"),
            self.config_data.get("double_space_dot", False)
        )
        self.hotkey_manager.triggered.connect(self.on_hotkey_triggered)

        # Connect Signals
        self.trigger_overlay_signal.connect(self.toggle_or_show_overlay)
        self.settings_window.config_saved.connect(self.on_config_saved)
        self.settings_window.test_wheel_requested.connect(self.overlay.show_at_cursor)

        # System Tray Icon Setup
        self.tray_icon = QSystemTrayIcon(create_circle_tray_icon(), parent=None)
        self.tray_icon.setToolTip("Circle - Radial Wheel Menu")

        tray_menu = QMenu()

        switcher_action = tray_menu.addAction("🪟 Windows Task View Switcher")
        switcher_action.triggered.connect(self.window_switcher_window.show_centered)

        app_search_action = tray_menu.addAction("🚀 Raycast App Launcher")
        app_search_action.triggered.connect(self.app_search_window.show_centered)

        voice_action = tray_menu.addAction("🎙️ Voice Typing Dictation")
        voice_action.triggered.connect(self.voice_typing_hud.trigger_voice_dictation)

        tray_menu.addSeparator()

        self.double_space_action = tray_menu.addAction("⌨️ Double Spacebar -> '.' (Mac style)")
        self.double_space_action.setCheckable(True)
        self.double_space_action.setChecked(self.config_data.get("double_space_dot", False))
        self.double_space_action.triggered.connect(self.toggle_double_space_dot)

        settings_action = tray_menu.addAction("⚙️ Settings & Customization")
        settings_action.triggered.connect(self.show_settings)

        test_action = tray_menu.addAction("⚡ Test Wheel Menu")
        test_action.triggered.connect(self.overlay.show_at_cursor)

        tray_menu.addSeparator()

        exit_action = tray_menu.addAction("❌ Exit Circle")
        exit_action.triggered.connect(self.exit_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

        # Start Hotkey Listener
        self.hotkey_manager.start()

        # Show notification on launch
        self.tray_icon.showMessage(
            "Circle is active!",
            f"Press '{self.config_data.get('hotkey', '<ctrl>+<space>')}' to open the radial wheel.",
            QSystemTrayIcon.Information,
            3000
        )

    def toggle_or_show_overlay(self):
        if self.overlay.isVisible():
            self.overlay.hide()
        else:
            self.overlay.show_at_cursor()

    def toggle_double_space_dot(self, checked):
        self.config_data["double_space_dot"] = checked
        save_config(self.config_data)
        self.hotkey_manager.update_settings(
            self.config_data.get("hotkey", "<ctrl>+<space>"),
            checked
        )
        if hasattr(self.settings_window, 'double_space_dot_checkbox'):
            self.settings_window.double_space_dot_checkbox.setChecked(checked)

    def on_hotkey_triggered(self):
        self.trigger_overlay_signal.emit()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClicked or reason == QSystemTrayIcon.Trigger:
            self.show_settings()

    def show_settings(self):
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def on_config_saved(self, new_config):
        self.config_data = new_config
        self.overlay.update_config(self.config_data)
        self.hotkey_manager.update_settings(
            self.config_data.get("hotkey", "<ctrl>+<space>"),
            self.config_data.get("double_space_dot", False)
        )
        if hasattr(self, 'double_space_action'):
            self.double_space_action.setChecked(self.config_data.get("double_space_dot", False))

    def exit_app(self):
        self.hotkey_manager.stop()
        self.tray_icon.hide()
        QApplication.quit()

def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    circle_app = CircleApp()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
