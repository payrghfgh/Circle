import os
import sys
import ctypes
from ctypes import wintypes
from PySide6.QtCore import Qt, Signal, QFileInfo, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel,
    QApplication, QFrame, QHBoxLayout, QFileIconProvider
)
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL

user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL

user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

def get_process_path(hwnd):
    try:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value:
            # PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            h_proc = kernel32.OpenProcess(0x1000, False, pid.value)
            if h_proc:
                buf = ctypes.create_unicode_buffer(512)
                size = wintypes.DWORD(512)
                if kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size)):
                    kernel32.CloseHandle(h_proc)
                    return buf.value
                kernel32.CloseHandle(h_proc)
    except Exception:
        pass
    return None

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
        self.container.setStyleSheet("""
            QFrame {
                background-color: #1E1E2E;
                border: 2px solid #CBA6F7;
                border-radius: 14px;
            }
            QLineEdit {
                background-color: #181825;
                border: 1px solid #45475A;
                border-radius: 10px;
                padding: 12px 16px;
                color: #CDD6F4;
                font-size: 16px;
                font-family: 'Segoe UI';
            }
            QLineEdit:focus {
                border: 1.5px solid #CBA6F7;
            }
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
                color: #CDD6F4;
                font-size: 14px;
                font-family: 'Segoe UI';
            }
            QListWidget::item {
                padding: 10px 14px;
                border-radius: 8px;
                margin-bottom: 3px;
            }
            QListWidget::item:hover {
                background-color: #313244;
            }
            QListWidget::item:selected {
                background-color: #CBA6F7;
                color: #11111B;
                font-weight: bold;
            }
            QLabel {
                color: #A6ADC8;
                font-size: 11px;
            }
        """)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title_label = QLabel("🪟 Windows Task View Switcher")
        title_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title_label.setStyleSheet("color: #CBA6F7;")
        header_layout.addWidget(title_label)

        self.status_label = QLabel("0 Windows Open")
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()

        esc_hint = QLabel("Esc to close")
        header_layout.addWidget(esc_hint)
        container_layout.addLayout(header_layout)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter open windows or press Enter to select... (e.g. Chrome, Code, Spotify)")
        self.search_input.textChanged.connect(self.on_search_changed)
        container_layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(28, 28))
        self.list_widget.itemDoubleClicked.connect(self.switch_to_selected)
        container_layout.addWidget(self.list_widget)

        layout.addWidget(self.container)

    def scan_open_windows(self):
        """Enumerates all currently open top-level application windows."""
        self.open_windows = []
        ignored_titles = [
            "Program Manager", "Settings", "Default IME", "MSCTFIME UI",
            "Windows Input Experience", "Task View", "Circle - Wheel Menu Customizer"
        ]

        @WNDENUMPROC
        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value.strip()

                    if title and title not in ignored_titles:
                        # Filter out tool windows or windows with no taskbar representation
                        ex_style = user32.GetWindowLongW(hwnd, -20)
                        if not (ex_style & 0x00000080):  # WS_EX_TOOLWINDOW
                            proc_path = get_process_path(hwnd)
                            self.open_windows.append({
                                "hwnd": hwnd,
                                "title": title,
                                "proc_path": proc_path
                            })
            return True

        user32.EnumWindows(enum_cb, 0)
        self.status_label.setText(f"{len(self.open_windows)} Open Windows")

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
            if not query or query in win["title"].lower():
                icon = self.get_window_icon(win["proc_path"])
                item = QListWidgetItem(f"🪟 {win['title']}")
                if not icon.isNull():
                    item.setIcon(icon)
                item.setData(Qt.UserRole, win["hwnd"])
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
        curr_item = self.list_widget.currentItem()
        if curr_item:
            hwnd = curr_item.data(Qt.UserRole)
            self.hide()
            try:
                # SW_RESTORE = 9
                user32.ShowWindow(hwnd, 9)
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
            except Exception as e:
                print(f"Error focusing window {hwnd}: {e}")
