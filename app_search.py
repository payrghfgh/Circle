import os
import sys
import json
import subprocess
import threading
from PySide6.QtCore import Qt, Signal, QFileInfo, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel,
    QApplication, QFrame, QHBoxLayout, QFileIconProvider
)
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor

class AppSearchWindow(QWidget):
    apps_indexed_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(600, 420)

        self.apps_list = []
        self.icon_provider = QFileIconProvider()
        self.apps_indexed_signal.connect(self.refresh_list_ui)

        self.init_ui()
        # Initial fast scan + background PowerShell Get-StartApps indexing
        self.index_applications()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.container = QFrame(self)
        self.container.setStyleSheet("""
            QFrame {
                background-color: #1E1E2E;
                border: 2px solid #89B4FA;
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
                border: 1.5px solid #89B4FA;
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
                background-color: #89B4FA;
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
        title_label = QLabel("🚀 Raycast App Launcher")
        title_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title_label.setStyleSheet("color: #89B4FA;")
        header_layout.addWidget(title_label)

        self.status_label = QLabel("Indexing installed apps...")
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()

        esc_hint = QLabel("Esc to close")
        header_layout.addWidget(esc_hint)
        container_layout.addLayout(header_layout)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search all applications on your PC... (e.g. Chrome, Spotify, Zen, Discord)")
        self.search_input.textChanged.connect(self.on_search_changed)
        container_layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(28, 28))
        self.list_widget.itemDoubleClicked.connect(self.launch_selected)
        container_layout.addWidget(self.list_widget)

        layout.addWidget(self.container)

    def show_centered(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 3
        self.move(x, y)
        self.search_input.clear()
        self.refresh_list_ui()
        self.show()
        self.raise_()
        self.activateWindow()
        self.search_input.setFocus()

    def index_applications(self):
        """Indexes all Windows Start Menu, Desktop, and Installed Apps."""
        def background_scanner():
            seen_names = set()
            new_apps = []

            # 1. Fast Scan Start Menu Shortcuts & Desktops
            search_dirs = [
                r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
                os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
                os.path.expandvars(r"%USERPROFILE%\Desktop"),
                r"C:\Users\Public\Desktop",
            ]

            for s_dir in search_dirs:
                if os.path.exists(s_dir):
                    for root, _, files in os.walk(s_dir):
                        for file in files:
                            if file.endswith(".lnk"):
                                app_name = file[:-4]
                                lower_name = app_name.lower()
                                if any(k in lower_name for k in ["uninstall", "help", "readme", "website", "documentation"]):
                                    continue
                                if lower_name not in seen_names:
                                    seen_names.add(lower_name)
                                    full_path = os.path.join(root, file)
                                    new_apps.append({
                                        "name": app_name,
                                        "target": full_path,
                                        "type": "path",
                                        "file_info": full_path
                                    })

            # 2. Query PowerShell Get-StartApps for UWP & Full System App Index
            try:
                ps_cmd = "powershell -ExecutionPolicy Bypass -Command \"Get-StartApps | ConvertTo-Json\""
                output = subprocess.check_output(ps_cmd, shell=True, text=True, timeout=10, encoding="utf-8", errors="ignore")
                if output and output.strip():
                    data = json.loads(output)
                    if isinstance(data, dict):
                        data = [data]
                    for entry in data:
                        name = entry.get("Name", "").strip()
                        appid = entry.get("AppID", "").strip()
                        lower_name = name.lower()

                        if not name or not appid or lower_name in seen_names:
                            continue
                        if any(k in lower_name for k in ["uninstall", "help", "readme", "website"]):
                            continue

                        seen_names.add(lower_name)

                        # Determine how to launch this app
                        if appid.endswith(".exe") or appid.endswith(".lnk") or os.path.exists(appid):
                            app_type = "path"
                            target = appid
                            file_info = appid
                        else:
                            app_type = "uwp"
                            target = appid
                            file_info = None

                        new_apps.append({
                            "name": name,
                            "target": target,
                            "type": app_type,
                            "file_info": file_info
                        })
            except Exception as e:
                print(f"Error querying Get-StartApps: {e}")

            # 3. Add Core System Apps if missing
            system_apps = [
                ("Notepad", "notepad.exe"),
                ("Calculator", "calc.exe"),
                ("File Explorer", "explorer.exe"),
                ("Task Manager", "taskmgr.exe"),
                ("Snipping Tool", "SnippingTool.exe"),
                ("Command Prompt", "cmd.exe"),
                ("PowerShell", "powershell.exe"),
                ("Control Panel", "control.exe"),
            ]
            for sys_name, sys_path in system_apps:
                if sys_name.lower() not in seen_names:
                    seen_names.add(sys_name.lower())
                    new_apps.append({
                        "name": sys_name,
                        "target": sys_path,
                        "type": "path",
                        "file_info": sys_path
                    })

            new_apps.sort(key=lambda x: x["name"].lower())
            self.apps_list = new_apps
            self.apps_indexed_signal.emit()

        threading.Thread(target=background_scanner, daemon=True).start()

    def refresh_list_ui(self):
        self.status_label.setText(f"{len(self.apps_list)} Apps Ready")
        self.on_search_changed(self.search_input.text())

    def get_app_icon(self, app):
        """Retrieves real Windows application icon."""
        if app.get("file_info") and os.path.exists(app["file_info"]):
            try:
                icon = self.icon_provider.icon(QFileInfo(app["file_info"]))
                if not icon.isNull():
                    return icon
            except Exception:
                pass
        return QIcon()

    def on_search_changed(self, text):
        query = text.strip().lower()
        self.list_widget.clear()

        count = 0
        for app in self.apps_list:
            if not query or query in app["name"].lower():
                icon = self.get_app_icon(app)
                item = QListWidgetItem(app["name"])
                if not icon.isNull():
                    item.setIcon(icon)
                item.setData(Qt.UserRole, app)
                self.list_widget.addItem(item)
                count += 1
                if count >= 30:
                    break

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.launch_selected()
        elif event.key() == Qt.Key_Down:
            curr = self.list_widget.currentRow()
            if curr < self.list_widget.count() - 1:
                self.list_widget.setCurrentRow(curr + 1)
        elif event.key() == Qt.Key_Up:
            curr = self.list_widget.currentRow()
            if curr > 0:
                self.list_widget.setCurrentRow(curr - 1)

    def launch_selected(self):
        curr_item = self.list_widget.currentItem()
        if curr_item:
            app_data = curr_item.data(Qt.UserRole)
            self.hide()
            try:
                target = app_data["target"]
                app_type = app_data["type"]

                if app_type == "uwp":
                    subprocess.Popen(f'explorer.exe "shell:AppsFolder\\{target}"', shell=True)
                else:
                    if os.path.exists(target):
                        os.startfile(target)
                    else:
                        subprocess.Popen(target, shell=True)
            except Exception as e:
                print(f"Error launching app {app_data}: {e}")
