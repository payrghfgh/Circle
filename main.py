import sys

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

import platform_layer as platform
import theme
import updater
from update_dialog import UpdateDialog, UpToDateDialog
from version import __version__ as APP_VERSION
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

    # macOS menu-bar icons are template images: drawn in black and inverted by
    # the system, so they stay legible in both light and dark menu bars.
    ink = QColor(0, 0, 0) if platform.IS_MACOS else QColor(theme.TEXT)
    core = QColor(0, 0, 0) if platform.IS_MACOS else QColor(theme.ACCENT)

    pen = painter.pen()
    pen.setColor(ink)
    pen.setWidthF(3.0)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(8, 8, 48, 48)

    painter.setPen(Qt.NoPen)
    painter.setBrush(core)
    painter.drawEllipse(24, 24, 16, 16)
    painter.end()

    icon = QIcon(pixmap)
    if platform.IS_MACOS:
        icon.setIsMask(True)
    return icon


class CircleApp(QObject):
    trigger_overlay_signal = Signal()

    def __init__(self):
        super().__init__()
        self.config_data = load_config()

        if self.config_data.get("autostart", True):
            set_autostart(True)

        # Windows are built the first time they are asked for. Nothing but the
        # tray icon and the hotkey listener exists while Circle sits idle.
        self._windows = {}

        self.hotkey_manager = HotkeyManager(
            self.config_data.get("hotkey", "<ctrl>+<space>"),
            self.config_data.get("double_space_dot", False),
            self.config_data.get("search_hotkey", "<alt>+<space>"),
        )
        self.hotkey_manager.triggered.connect(self.toggle_or_show_overlay)
        self.hotkey_manager.search_triggered.connect(self.toggle_search)

        self._build_tray()
        self.hotkey_manager.start()

        self._update_thread = None
        self._update_dialog = None
        self._up_to_date_dialog = None
        QTimer.singleShot(4000, self._auto_check_updates)

        message = (
            f"Press {self._pretty(self.config_data.get('search_hotkey', '<alt>+<space>'))} "
            "to search, or the tray icon for the wheel."
        )
        if platform.IS_MACOS:
            message += ("  If the shortcut does nothing, allow Circle under "
                        "System Settings → Privacy & Security → Accessibility.")
        self.tray_icon.showMessage("Circle is running", message,
                                   QSystemTrayIcon.Information, 6000)

    # ----------------------------------------------------------------- tray --

    def _build_tray(self):
        self.tray_icon = QSystemTrayIcon(create_tray_icon(), parent=None)
        self.tray_icon.setToolTip(f"Circle {APP_VERSION}")

        menu = QMenu()

        search_action = menu.addAction("Search…")
        search_action.setShortcutVisibleInContextMenu(True)
        search_action.triggered.connect(self.show_search)
        menu.addSeparator()

        switcher_action = menu.addAction("Switch windows")
        switcher_action.triggered.connect(lambda: self._switcher().show_centered())

        voice_action = menu.addAction("Voice typing")
        voice_action.triggered.connect(lambda: self._voice_hud().trigger_voice_dictation())

        wheel_action = menu.addAction("Radial wheel")
        wheel_action.triggered.connect(lambda: self._overlay().show_at_cursor())

        menu.addSeparator()

        self.double_space_action = menu.addAction("Double space makes a period")
        self.double_space_action.setCheckable(True)
        self.double_space_action.setChecked(self.config_data.get("double_space_dot", False))
        self.double_space_action.triggered.connect(self.toggle_double_space_dot)

        updates_action = menu.addAction("Check for updates…")
        updates_action.triggered.connect(lambda: self.check_for_updates(manual=True))

        settings_action = menu.addAction("Settings…")
        settings_action.triggered.connect(self.show_settings)

        menu.addSeparator()

        exit_action = menu.addAction("Quit Circle")
        exit_action.triggered.connect(self.exit_app)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    # ------------------------------------------------------- lazy windows --

    def _register_special(self):
        register_special_windows(self._windows.get("search"),
                                 self._windows.get("voice"),
                                 self._windows.get("switcher"))

    def _search_window(self) -> SearchWindow:
        window = self._windows.get("search")
        if window is None:
            window = SearchWindow()
            window.action_failed.connect(self._on_action_failed)
            self._windows["search"] = window
            self._register_special()
        return window

    def _overlay(self) -> WheelOverlay:
        window = self._windows.get("overlay")
        if window is None:
            window = WheelOverlay(self.config_data)
            self._windows["overlay"] = window
        return window

    def _switcher(self) -> WindowSwitcherWindow:
        window = self._windows.get("switcher")
        if window is None:
            window = WindowSwitcherWindow()
            self._windows["switcher"] = window
            self._register_special()
        return window

    def _voice_hud(self) -> VoiceTypingHUD:
        window = self._windows.get("voice")
        if window is None:
            window = VoiceTypingHUD()
            self._windows["voice"] = window
            self._register_special()
        return window

    def _settings_window(self) -> SettingsWindow:
        window = self._windows.get("settings")
        if window is None:
            window = SettingsWindow(self.config_data)
            window.config_saved.connect(self.on_config_saved)
            window.test_wheel_requested.connect(lambda: self._overlay().show_at_cursor())
            window.check_updates_requested.connect(
                lambda: self.check_for_updates(manual=True)
            )
            self._windows["settings"] = window
        return window

    @staticmethod
    def _pretty(hotkey: str) -> str:
        text = hotkey.replace("<", "").replace(">", "")
        return text.replace("+", " + ").title()

    # -------------------------------------------------------------- actions --

    def show_search(self):
        window = self._search_window()
        if window.isVisible():
            window.dismiss()
        else:
            window.show_centered()

    def toggle_search(self):
        self.show_search()

    def toggle_or_show_overlay(self):
        overlay = self._overlay()
        if overlay.isVisible():
            overlay.hide()
        else:
            overlay.show_at_cursor()

    def toggle_double_space_dot(self, checked):
        self.config_data["double_space_dot"] = checked
        save_config(self.config_data)
        self.hotkey_manager.update_settings(
            self.config_data.get("hotkey", "<ctrl>+<space>"),
            checked,
            self.config_data.get("search_hotkey", "<alt>+<space>"),
        )
        settings = self._windows.get("settings")
        if settings is not None and hasattr(settings, "double_space_dot_checkbox"):
            settings.double_space_dot_checkbox.setChecked(checked)

    def on_tray_icon_activated(self, reason):
        # On macOS a single click already opens the menu bar menu, so only a
        # double click should summon the panel. Windows has no such menu.
        if platform.IS_MACOS:
            if reason == QSystemTrayIcon.DoubleClicked:
                self.show_search()
            return
        if reason in (QSystemTrayIcon.DoubleClicked, QSystemTrayIcon.Trigger):
            self.show_search()

    def show_settings(self):
        window = self._settings_window()
        window.show()
        window.raise_()
        window.activateWindow()

    def _on_action_failed(self, message: str):
        """A windowed build has no console, so failures go to a notification."""
        print(f"[circle] action failed: {message}")
        self.tray_icon.showMessage("Circle", message,
                                   QSystemTrayIcon.Warning, 6000)

    def on_config_saved(self, new_config):
        self.config_data = new_config
        overlay = self._windows.get("overlay")
        if overlay is not None:
            overlay.update_config(self.config_data)
        self.hotkey_manager.update_settings(
            self.config_data.get("hotkey", "<ctrl>+<space>"),
            self.config_data.get("double_space_dot", False),
            self.config_data.get("search_hotkey", "<alt>+<space>"),
        )
        self.double_space_action.setChecked(
            self.config_data.get("double_space_dot", False)
        )
        search = self._windows.get("search")
        if search is not None:
            search.engine.start_file_index(force=True)

    # --------------------------------------------------------------- updates --

    def _auto_check_updates(self):
        if not updater.platform_has_updates():
            return
        if not updater.should_auto_check(self.config_data):
            return
        self.check_for_updates(manual=False)

    def check_for_updates(self, manual: bool = False):
        if self._update_thread is not None and self._update_thread.isRunning():
            return

        updater.clear_downloads()
        self._update_thread = updater.UpdateCheckThread(parent=self)
        self._update_thread.found.connect(self._on_update_found)
        self._update_thread.current.connect(
            lambda v: self._on_update_current(v, manual)
        )
        self._update_thread.failed.connect(
            lambda message: self._on_update_failed(message, manual)
        )
        self._update_thread.start()

    def _record_check(self):
        updater.mark_checked(self.config_data)
        save_config(self.config_data)

    def _on_update_found(self, info):
        self._record_check()
        if self._update_dialog is not None and self._update_dialog.isVisible():
            return
        self._update_dialog = UpdateDialog(info)
        self._update_dialog.dismissed.connect(self._on_update_dialog_closed)
        self._update_dialog.show_centered()

    def _on_update_dialog_closed(self):
        self._update_dialog = None

    def _on_update_current(self, version, manual):
        self._record_check()
        if not manual:
            return
        self._up_to_date_dialog = UpToDateDialog(version)
        self._up_to_date_dialog.show_centered()

    def _on_update_failed(self, message, manual):
        self._record_check()
        print(f"[circle] update check: {message}")
        if manual:
            self.tray_icon.showMessage("Update check failed", message,
                                       QSystemTrayIcon.Warning, 6000)

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
