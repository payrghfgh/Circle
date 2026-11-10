import sys

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

import theme
from action_executor import register_special_windows, set_autostart
from config import load_config, save_config
from hotkey_manager import HotkeyManager
from search_window import SearchWindow
from settings_gui import SettingsWindow
from voice_typing import VoiceTypingHUD
from wheel_overlay import WheelOverlay
from window_switcher import WindowSwitcherWindow


def create_tray_icon():
    """The wheel, reduced to a mark: one ring, one core."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setPen(QColor(theme.TEXT))
    pen = painter.pen()
    pen.setWidthF(3.0)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(8, 8, 48, 48)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(theme.ACCENT))
    painter.drawEllipse(24, 24, 16, 16)
    painter.end()
    return QIcon(pixmap)


class CircleApp(QObject):
    trigger_overlay_signal = Signal()

    def __init__(self):
        super().__init__()
        self.config_data = load_config()

        if self.config_data.get("autostart", True):
            set_autostart(True)

        # Windows that other parts of the app can summon by action type.
        self.search_window = SearchWindow()
        self.voice_typing_hud = VoiceTypingHUD()
        self.window_switcher_window = WindowSwitcherWindow()
        register_special_windows(self.search_window, self.voice_typing_hud,
                                 self.window_switcher_window)

        self.overlay = WheelOverlay(self.config_data)
        self.settings_window = SettingsWindow(self.config_data)

        self.hotkey_manager = HotkeyManager(
            self.config_data.get("hotkey", "<ctrl>+<space>"),
            self.config_data.get("double_space_dot", False),
            self.config_data.get("search_hotkey", "<alt>+<space>"),
        )
        self.hotkey_manager.triggered.connect(self.toggle_or_show_overlay)
        self.hotkey_manager.search_triggered.connect(self.toggle_search)

        self.settings_window.config_saved.connect(self.on_config_saved)
        self.settings_window.test_wheel_requested.connect(self.overlay.show_at_cursor)

        self._build_tray()
        self.hotkey_manager.start()

        self.tray_icon.showMessage(
            "Circle is running",
            f"Press {self._pretty(self.config_data.get('search_hotkey', '<alt>+<space>'))} "
            "to search, or the tray icon for the wheel.",
            QSystemTrayIcon.Information,
            3500,
        )

    # ----------------------------------------------------------------- tray --

    def _build_tray(self):
        self.tray_icon = QSystemTrayIcon(create_tray_icon(), parent=None)
        self.tray_icon.setToolTip("Circle")

        menu = QMenu()

        search_action = menu.addAction("Search…")
        search_action.setShortcutVisibleInContextMenu(True)
        search_action.triggered.connect(self.show_search)
        menu.addSeparator()

        switcher_action = menu.addAction("Switch windows")
        switcher_action.triggered.connect(self.window_switcher_window.show_centered)

        voice_action = menu.addAction("Voice typing")
        voice_action.triggered.connect(self.voice_typing_hud.trigger_voice_dictation)

        wheel_action = menu.addAction("Radial wheel")
        wheel_action.triggered.connect(self.overlay.show_at_cursor)

        menu.addSeparator()

        self.double_space_action = menu.addAction("Double space makes a period")
        self.double_space_action.setCheckable(True)
        self.double_space_action.setChecked(self.config_data.get("double_space_dot", False))
        self.double_space_action.triggered.connect(self.toggle_double_space_dot)

        settings_action = menu.addAction("Settings…")
        settings_action.triggered.connect(self.show_settings)

        menu.addSeparator()

        exit_action = menu.addAction("Quit Circle")
        exit_action.triggered.connect(self.exit_app)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    @staticmethod
    def _pretty(hotkey: str) -> str:
        text = hotkey.replace("<", "").replace(">", "")
        return text.replace("+", " + ").title()

    # -------------------------------------------------------------- actions --

    def show_search(self):
        if self.search_window.isVisible():
            self.search_window.dismiss()
        else:
            self.search_window.show_centered()

    def toggle_search(self):
        self.show_search()

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
            checked,
            self.config_data.get("search_hotkey", "<alt>+<space>"),
        )
        if hasattr(self.settings_window, "double_space_dot_checkbox"):
            self.settings_window.double_space_dot_checkbox.setChecked(checked)

    def on_tray_icon_activated(self, reason):
        if reason in (QSystemTrayIcon.DoubleClicked, QSystemTrayIcon.Trigger):
            self.show_search()

    def show_settings(self):
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def on_config_saved(self, new_config):
        self.config_data = new_config
        self.overlay.update_config(self.config_data)
        self.hotkey_manager.update_settings(
            self.config_data.get("hotkey", "<ctrl>+<space>"),
            self.config_data.get("double_space_dot", False),
            self.config_data.get("search_hotkey", "<alt>+<space>"),
        )
        self.double_space_action.setChecked(
            self.config_data.get("double_space_dot", False)
        )
        self.search_window.engine.start_file_index(force=True)

    def exit_app(self):
        self.hotkey_manager.stop()
        self.tray_icon.hide()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Circle")
    app.setApplicationDisplayName("Circle")
    app.setQuitOnLastWindowClosed(False)
    theme.apply_app_theme(app)

    circle = CircleApp()  # noqa: F841 - kept alive for the app's lifetime
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
