import os

from PySide6.QtCore import Qt, QFileInfo, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel,
    QApplication, QFrame, QHBoxLayout, QFileIconProvider
)
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor

import platform_layer as platform
import theme


def get_process_path(hwnd):
    """Kept for callers that still pass a window handle."""
    return ""


class WindowSwitcherWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(620, 440)

        self.open_windows = []
        self.icon_provider = QFileIconProvider()

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.container = QFrame(self)
        self.container.setObjectName("panel")
        theme.panel_shadow(self.container, blur=64, y_offset=18, alpha=190)
        self.container.setStyleSheet(theme.switcher_qss())

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title_label = QLabel("Switch windows")
        title_label.setFont(theme.font(14, QFont.DemiBold, display=True))
        header_layout.addWidget(title_label)

        self.status_label = QLabel("0 open")
        self.status_label.setFont(theme.font(11))
        self.status_label.setStyleSheet(f"color: {theme.TEXT_DIM};")
        header_layout.addWidget(self.status_label, 0, Qt.AlignBottom)
        header_layout.addStretch()

        esc_hint = QLabel("esc to close")
        esc_hint.setFont(theme.font(11))
        esc_hint.setStyleSheet(f"color: {theme.TEXT_DIM};")
        header_layout.addWidget(esc_hint)
        container_layout.addLayout(header_layout)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("query")
        self.search_input.setFont(theme.font(17, QFont.Normal, display=True))
        self.search_input.setPlaceholderText("Filter open windows")
        self.search_input.textChanged.connect(self.on_search_changed)
        container_layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("results")
        self.list_widget.setIconSize(QSize(26, 26))
        self.list_widget.setFocusPolicy(Qt.NoFocus)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list_widget.itemDoubleClicked.connect(self.switch_to_selected)
        container_layout.addWidget(self.list_widget)

        layout.addWidget(self.container)

    def scan_open_windows(self):
        """Every top-level window you could switch to."""
        self.open_windows = platform.list_windows()
        count = len(self.open_windows)
        self.status_label.setText(f"{count} open" if count else "nothing to switch to")

    def show_centered(self):
        self.scan_open_windows()
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 3
        self.move(x, y)
        self.search_input.clear()
        self.on_search_changed("")
        self.show()
        self.raise_()
        self.activateWindow()
        self.search_input.setFocus()

    def get_window_icon(self, proc_path):
        if proc_path and os.path.exists(proc_path):
            try:
                icon = self.icon_provider.icon(QFileInfo(proc_path))
                if not icon.isNull():
                    return icon
            except Exception:
                pass
        return QIcon()

    def on_search_changed(self, text):
        query = text.strip().lower()
        self.list_widget.clear()

        for win in self.open_windows:
            title = win.get("title") or win.get("app") or ""
            if not query or query in title.lower() or query in (win.get("app") or "").lower():
                icon = self.get_window_icon(win.get("proc_path", ""))
                label = title
                app_name = win.get("app") or ""
                if app_name and app_name.lower() not in title.lower():
                    label = f"{title}   ·   {app_name}"
                item = QListWidgetItem(label)
                if not icon.isNull():
                    item.setIcon(icon)
                item.setData(Qt.UserRole, win.get("handle"))
                self.list_widget.addItem(item)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.switch_to_selected()
        elif event.key() == Qt.Key_Down:
            curr = self.list_widget.currentRow()
            if curr < self.list_widget.count() - 1:
                self.list_widget.setCurrentRow(curr + 1)
        elif event.key() == Qt.Key_Up:
            curr = self.list_widget.currentRow()
            if curr > 0:
                self.list_widget.setCurrentRow(curr - 1)

    def switch_to_selected(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        handle = item.data(Qt.UserRole)
        self.hide()
        platform.activate_window(handle)
