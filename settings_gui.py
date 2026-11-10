import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QGroupBox, QFormLayout, QFileDialog, QTabWidget,
    QColorDialog, QMessageBox, QFrame, QScrollArea, QGridLayout, QSpinBox,
    QCheckBox
)
from PySide6.QtGui import QFont, QIcon, QColor, QPainter, QBrush, QPen
from config import save_config, DEFAULT_CONFIG
from action_executor import set_autostart, get_autostart

PRESET_EMOJIS = ["🪟", "🚀", "🎙️", "🔊", "🔉", "🔇", "🌐", "📸", "📝", "⚙️", "📁", "🎮", "🎵", "💻", "⚡", "🔍", "🛑", "⭐", "⏯️", "⏭️", "⏮️", "🧮", "✂️", "🔒"]
PRESET_COLORS = ["#89B4FA", "#A6E3A1", "#FAB387", "#F38BA8", "#CBA6F7", "#F9E2AF", "#74C7EC", "#94E2D5"]

ACTION_PRESETS = [
    {"name": "Window Switcher", "icon": "🪟", "type": "window_switcher", "detail": "", "color": "#CBA6F7"},
    {"name": "Raycast App Search", "icon": "🚀", "type": "app_search", "detail": "", "color": "#89B4FA"},
    {"name": "Voice-to-Text", "icon": "🎙️", "type": "voice_to_text", "detail": "", "color": "#A6E3A1"},
    {"name": "Volume Up", "icon": "🔊", "type": "volume", "detail": "up", "color": "#89B4FA"},
    {"name": "Volume Down", "icon": "🔉", "type": "volume", "detail": "down", "color": "#F38BA8"},
    {"name": "Mute Audio", "icon": "🔇", "type": "volume", "detail": "mute", "color": "#F9E2AF"},
    {"name": "Play / Pause", "icon": "⏯️", "type": "media", "detail": "playpause", "color": "#A6E3A1"},
    {"name": "Next Track", "icon": "⏭️", "type": "media", "detail": "next", "color": "#74C7EC"},
    {"name": "Prev Track", "icon": "⏮️", "type": "media", "detail": "prev", "color": "#74C7EC"},
    {"name": "Screenshot", "icon": "📸", "type": "system", "detail": "screenshot", "color": "#FAB387"},
    {"name": "Screen Snippet", "icon": "✂️", "type": "system", "detail": "snip", "color": "#FAB387"},
    {"name": "Calculator", "icon": "🧮", "type": "system", "detail": "calc", "color": "#CBA6F7"},
    {"name": "Notepad", "icon": "📝", "type": "system", "detail": "notepad", "color": "#CBA6F7"},
    {"name": "File Explorer", "icon": "📁", "type": "system", "detail": "explorer", "color": "#F9E2AF"},
    {"name": "Task Manager", "icon": "💻", "type": "system", "detail": "taskmgr", "color": "#89B4FA"},
    {"name": "Windows Settings", "icon": "⚙️", "type": "system", "detail": "settings", "color": "#94E2D5"},
    {"name": "Lock Screen", "icon": "🔒", "type": "system", "detail": "lock", "color": "#F38BA8"},
    {"name": "Show Desktop", "icon": "🖥️", "type": "system", "detail": "show_desktop", "color": "#89B4FA"},
    {"name": "Google", "icon": "🌐", "type": "open_url", "detail": "https://google.com", "color": "#A6E3A1"},
    {"name": "YouTube", "icon": "🎥", "type": "open_url", "detail": "https://youtube.com", "color": "#F38BA8"},
    {"name": "ChatGPT", "icon": "💬", "type": "open_url", "detail": "https://chatgpt.com", "color": "#94E2D5"},
    {"name": "GitHub", "icon": "💻", "type": "open_url", "detail": "https://github.com", "color": "#CDD6F4"},
    {"name": "Web Search", "icon": "🔍", "type": "web_search", "detail": "Python tutorial", "color": "#89B4FA"},
    {"name": "Copy (Ctrl+C)", "icon": "📋", "type": "keyboard", "detail": "ctrl+c", "color": "#FAB387"},
    {"name": "Paste (Ctrl+V)", "icon": "📌", "type": "keyboard", "detail": "ctrl+v", "color": "#A6E3A1"},
]

class WheelPreviewWidget(QWidget):
    """Mini visual representation of the radial wheel with dynamic slot count."""
    def __init__(self, slots_data):
        super().__init__()
        self.slots_data = slots_data
        self.setMinimumSize(230, 230)
        self.selected_slot_index = 0

    def set_slots(self, slots_data, selected_idx=0):
        self.slots_data = slots_data
        self.selected_slot_index = selected_idx
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx, cy = w / 2.0, h / 2.0
        outer_r = min(w, h) / 2.0 - 15
        inner_r = 35.0

        num_slots = max(1, len(self.slots_data))
        span_angle = 360.0 / num_slots

        rect_outer = (cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)
        rect_inner = (cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)

        for i, slot in enumerate(self.slots_data):
            start_deg = 90 - (i * span_angle)
            end_deg = 90 - ((i + 1) * span_angle)

            from PySide6.QtGui import QPainterPath
            path = QPainterPath()
            path.arcMoveTo(*rect_outer, start_deg)
            path.arcTo(*rect_outer, start_deg, -span_angle)
            path.arcTo(*rect_inner, end_deg, span_angle)
            path.closeSubpath()

            is_sel = (i == self.selected_slot_index)
            color_str = slot.get("color", "#89B4FA")
            accent_color = QColor(color_str)

            if is_sel:
                painter.setBrush(QBrush(accent_color))
                painter.setPen(QPen(Qt.white, 2.5))
            else:
                bg = QColor(30, 30, 46, 200)
                painter.setBrush(QBrush(bg))
                painter.setPen(QPen(QColor(255, 255, 255, 40), 1))

            painter.drawPath(path)

            mid_deg = (start_deg + end_deg) / 2.0
            import math
            mid_rad = math.radians(mid_deg)
            lr = (inner_r + outer_r) / 2.0
            lx = cx + lr * math.cos(mid_rad)
            ly = cy - lr * math.sin(mid_rad)

            painter.setPen(Qt.white if is_sel else QColor(205, 214, 244))
            font = QFont("Segoe UI Emoji", 10 if num_slots <= 8 else 8)
            painter.setFont(font)
            painter.drawText(int(lx - 15), int(ly - 12), 30, 24, Qt.AlignCenter, slot.get("icon", "★"))

        # Center hub
        painter.setBrush(QBrush(QColor(17, 17, 27)))
        painter.setPen(QPen(QColor(137, 180, 250), 2))
        painter.drawEllipse(int(cx - inner_r), int(cy - inner_r), int(inner_r * 2), int(inner_r * 2))

        painter.setPen(Qt.white)
        font = QFont("Segoe UI", 8, QFont.Bold)
        painter.setFont(font)
        painter.drawText(int(cx - inner_r), int(cy - 10), int(inner_r * 2), 20, Qt.AlignCenter, f"{num_slots} Slots")


class SettingsWindow(QMainWindow):
    config_saved = Signal(dict)
    test_wheel_requested = Signal()

    def __init__(self, config_data):
        super().__init__()
        self.config_data = config_data.copy()
        self.slots_data = [dict(s) for s in self.config_data.get("slots", [])]

        self.setWindowTitle("Circle - Wheel Menu Customizer")
        self.resize(880, 640)
        self.setMinimumSize(800, 560)

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1E1E2E;
                color: #CDD6F4;
                font-family: 'Segoe UI', sans-serif;
            }
            QGroupBox {
                border: 1px solid #313244;
                border-radius: 8px;
                margin-top: 12px;
                font-weight: bold;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #89B4FA;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #181825;
                border: 1px solid #45475A;
                border-radius: 6px;
                padding: 6px 10px;
                color: #CDD6F4;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #89B4FA;
            }
            QCheckBox {
                color: #CDD6F4;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #313244;
                border: 1px solid #45475A;
                border-radius: 6px;
                padding: 8px 14px;
                color: #CDD6F4;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45475A;
                border: 1px solid #89B4FA;
            }
            QPushButton#presetBtn {
                background-color: #181825;
                border: 1px solid #313244;
                text-align: left;
                padding: 6px 10px;
                font-size: 12px;
            }
            QPushButton#presetBtn:hover {
                background-color: #313244;
                border: 1px solid #89B4FA;
            }
            QPushButton#saveBtn {
                background-color: #89B4FA;
                color: #11111B;
                border: none;
            }
            QPushButton#saveBtn:hover {
                background-color: #B4BEFE;
            }
            QPushButton#testBtn {
                background-color: #A6E3A1;
                color: #11111B;
                border: none;
            }
            QPushButton#testBtn:hover {
                background-color: #94E2D5;
            }
            QTabWidget::pane {
                border: 1px solid #313244;
                border-radius: 8px;
                background: #181825;
            }
            QTabBar::tab {
                background: #1E1E2E;
                color: #A6ADC8;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #313244;
                color: #89B4FA;
                font-weight: bold;
            }
        """)

        # Header Title
        header_layout = QHBoxLayout()
        title_label = QLabel("⭕ Circle Wheel Customizer")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.test_btn = QPushButton("⚡ Test Wheel")
        self.test_btn.setObjectName("testBtn")
        self.test_btn.clicked.connect(lambda: self.test_wheel_requested.emit())
        header_layout.addWidget(self.test_btn)

        main_layout.addLayout(header_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        # Hotkey & Options Group
        hotkey_box = QGroupBox("⌨️ Trigger Shortcut & Settings")
        hotkey_layout = QFormLayout(hotkey_box)
        hotkey_layout.setContentsMargins(10, 14, 10, 10)

        self.hotkey_input = QLineEdit(self.config_data.get("hotkey", "<ctrl>+<space>"))
        self.hotkey_input.setPlaceholderText("e.g. <ctrl>+<space>, <alt>+<space>, middle_click")
        hotkey_layout.addRow("Shortcut:", self.hotkey_input)

        preset_layout = QHBoxLayout()
        btn_ctrl_space = QPushButton("Ctrl+Space")
        btn_ctrl_space.clicked.connect(lambda: self.hotkey_input.setText("<ctrl>+<space>"))
        btn_alt_space = QPushButton("Alt+Space")
        btn_alt_space.clicked.connect(lambda: self.hotkey_input.setText("<alt>+<space>"))
        btn_mid_click = QPushButton("Middle Click")
        btn_mid_click.clicked.connect(lambda: self.hotkey_input.setText("middle_click"))
        preset_layout.addWidget(btn_ctrl_space)
        preset_layout.addWidget(btn_alt_space)
        preset_layout.addWidget(btn_mid_click)
        hotkey_layout.addRow("Presets:", preset_layout)

        slot_ctrl_layout = QHBoxLayout()
        self.slot_count_spin = QSpinBox()
        self.slot_count_spin.setRange(3, 12)
        self.slot_count_spin.setValue(len(self.slots_data))
        self.slot_count_spin.valueChanged.connect(self.on_slot_count_changed)
        slot_ctrl_layout.addWidget(self.slot_count_spin)

        btn_add_slot = QPushButton("➕ Add Slot")
        btn_add_slot.clicked.connect(self.add_slot)
        btn_rem_slot = QPushButton("➖ Remove Slot")
        btn_rem_slot.clicked.connect(self.remove_slot)
        slot_ctrl_layout.addWidget(btn_add_slot)
        slot_ctrl_layout.addWidget(btn_rem_slot)
        hotkey_layout.addRow("Wheel Slots:", slot_ctrl_layout)

        self.autostart_checkbox = QCheckBox("🚀 Run automatically on Windows Startup")
        is_auto = self.config_data.get("autostart", True) or get_autostart()
        self.autostart_checkbox.setChecked(is_auto)
        hotkey_layout.addRow("Startup:", self.autostart_checkbox)

        self.double_space_dot_checkbox = QCheckBox("⌨️ Double Spacebar produces period '.' (Mac style)")
        is_ds_dot = self.config_data.get("double_space_dot", False)
        self.double_space_dot_checkbox.setChecked(is_ds_dot)
        hotkey_layout.addRow("Mac Typing:", self.double_space_dot_checkbox)

        left_col.addWidget(hotkey_box)

        # Quick Presets Gallery Box
        preset_gallery_box = QGroupBox("💡 1-Click Action Presets Gallery")
        preset_gallery_layout = QVBoxLayout(preset_gallery_box)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(140)
        scroll_content = QWidget()
        grid = QGridLayout(scroll_content)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setSpacing(6)

        for idx, item in enumerate(ACTION_PRESETS):
            pbtn = QPushButton(f"{item['icon']} {item['name']}")
            pbtn.setObjectName("presetBtn")
            pbtn.clicked.connect(lambda _, p=item: self.apply_action_preset(p))
            row = idx // 2
            col = idx % 2
            grid.addWidget(pbtn, row, col)

        scroll.setWidget(scroll_content)
        preset_gallery_layout.addWidget(scroll)

        left_col.addWidget(preset_gallery_box)

        # Wheel Preview Box
        preview_box = QGroupBox("🎡 Live Wheel Preview")
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setAlignment(Qt.AlignCenter)

        self.wheel_preview = WheelPreviewWidget(self.slots_data)
        preview_layout.addWidget(self.wheel_preview)

        left_col.addWidget(preview_box)
        left_col.addStretch()

        content_layout.addLayout(left_col, 1)

        # Right Column: Dynamic Slots Customizer Tabs
        right_col = QVBoxLayout()
        slots_group = QGroupBox("⚙️ Customize Active Wheel Slots")
        slots_layout = QVBoxLayout(slots_group)

        self.tabs = QTabWidget()
        self.rebuild_slot_tabs()

        self.tabs.currentChanged.connect(self.on_tab_changed)
        slots_layout.addWidget(self.tabs)
        right_col.addWidget(slots_group)

        content_layout.addLayout(right_col, 2)
        main_layout.addLayout(content_layout)

        # Bottom Buttons
        bottom_layout = QHBoxLayout()

        reset_btn = QPushButton("🔄 Reset Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        bottom_layout.addWidget(reset_btn)

        bottom_layout.addStretch()

        save_btn = QPushButton("💾 Save & Apply")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.save_settings)
        bottom_layout.addWidget(save_btn)

        main_layout.addLayout(bottom_layout)

    def apply_action_preset(self, preset_dict):
        curr_idx = self.tabs.currentIndex()
        if 0 <= curr_idx < len(self.slots_data):
            self.slots_data[curr_idx]["name"] = preset_dict["name"]
            self.slots_data[curr_idx]["icon"] = preset_dict["icon"]
            self.slots_data[curr_idx]["action_type"] = preset_dict["type"]
            self.slots_data[curr_idx]["action_detail"] = preset_dict["detail"]
            self.slots_data[curr_idx]["color"] = preset_dict["color"]
            
            self.rebuild_slot_tabs()
            self.tabs.setCurrentIndex(curr_idx)
            self.wheel_preview.set_slots(self.slots_data, curr_idx)

    def rebuild_slot_tabs(self):
        curr_idx = max(0, self.tabs.currentIndex())
        self.tabs.clear()
        self.slot_editors = []

        for i, slot_data in enumerate(self.slots_data):
            editor_widget = self.create_slot_editor_widget(i, slot_data)
            self.slot_editors.append(editor_widget)
            tab_name = f"Slot {i+1}: {slot_data.get('name', 'Unassigned')}"
            self.tabs.addTab(editor_widget, tab_name)

        target_idx = min(curr_idx, len(self.slots_data) - 1)
        if target_idx >= 0:
            self.tabs.setCurrentIndex(target_idx)

    def on_slot_count_changed(self, new_count):
        curr_count = len(self.slots_data)
        if new_count > curr_count:
            for i in range(curr_count, new_count):
                default_colors = ["#89B4FA", "#A6E3A1", "#FAB387", "#F38BA8", "#CBA6F7", "#F9E2AF", "#74C7EC", "#94E2D5"]
                color_idx = i % len(default_colors)
                new_slot = {
                    "id": i + 1,
                    "name": f"New Slot {i+1}",
                    "icon": "★",
                    "action_type": "open_url",
                    "action_detail": "https://google.com",
                    "color": default_colors[color_idx]
                }
                self.slots_data.append(new_slot)
        elif new_count < curr_count:
            self.slots_data = self.slots_data[:new_count]

        self.rebuild_slot_tabs()
        self.wheel_preview.set_slots(self.slots_data, self.tabs.currentIndex())

    def add_slot(self):
        if len(self.slots_data) < 12:
            self.slot_count_spin.setValue(len(self.slots_data) + 1)

    def remove_slot(self):
        if len(self.slots_data) > 3:
            self.slot_count_spin.setValue(len(self.slots_data) - 1)

    def create_slot_editor_widget(self, index, slot_data):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(12)

        name_input = QLineEdit(slot_data.get("name", ""))
        name_input.textChanged.connect(lambda t, idx=index: self.on_slot_field_changed(idx, "name", t))
        layout.addRow("Slot Name:", name_input)

        icon_layout = QHBoxLayout()
        icon_input = QLineEdit(slot_data.get("icon", "★"))
        icon_input.setFixedWidth(60)
        icon_input.textChanged.connect(lambda t, idx=index: self.on_slot_field_changed(idx, "icon", t))
        icon_layout.addWidget(icon_input)

        emoji_scroll = QScrollArea()
        emoji_scroll.setFixedHeight(40)
        emoji_scroll.setWidgetResizable(True)
        emoji_container = QWidget()
        emoji_lay = QHBoxLayout(emoji_container)
        emoji_lay.setContentsMargins(0, 0, 0, 0)
        emoji_lay.setSpacing(4)

        for emo in PRESET_EMOJIS:
            ebtn = QPushButton(emo)
            ebtn.setFixedSize(30, 30)
            ebtn.clicked.connect(lambda _, e=emo, inp=icon_input: inp.setText(e))
            emoji_lay.addWidget(ebtn)

        emoji_scroll.setWidget(emoji_container)
        icon_layout.addWidget(emoji_scroll)
        layout.addRow("Icon / Emoji:", icon_layout)

        color_layout = QHBoxLayout()
        color_btn = QPushButton()
        curr_color = slot_data.get("color", "#89B4FA")
        color_btn.setStyleSheet(f"background-color: {curr_color}; border: 1px solid #FFFFFF; border-radius: 4px;")
        color_btn.setFixedSize(60, 26)

        def pick_color(idx=index, btn=color_btn):
            c = QColorDialog.getColor(QColor(self.slots_data[idx].get("color", "#89B4FA")), self)
            if c.isValid():
                hex_c = c.name()
                btn.setStyleSheet(f"background-color: {hex_c}; border: 1px solid #FFFFFF; border-radius: 4px;")
                self.on_slot_field_changed(idx, "color", hex_c)

        color_btn.clicked.connect(pick_color)
        color_layout.addWidget(color_btn)

        for hex_c in PRESET_COLORS:
            cp_btn = QPushButton()
            cp_btn.setStyleSheet(f"background-color: {hex_c}; border-radius: 4px;")
            cp_btn.setFixedSize(24, 24)
            cp_btn.clicked.connect(lambda _, hc=hex_c, idx=index, btn=color_btn: (
                btn.setStyleSheet(f"background-color: {hc}; border: 1px solid #FFFFFF; border-radius: 4px;"),
                self.on_slot_field_changed(idx, "color", hc)
            ))
            color_layout.addWidget(cp_btn)

        color_layout.addStretch()
        layout.addRow("Accent Color:", color_layout)

        type_combo = QComboBox()
        type_combo.addItems([
            "Window Switcher (Task View)",
            "Raycast App Launcher (Search & Open)",
            "Voice-to-Text Dictation",
            "System Volume (Adjust/Mute)",
            "Media Control (Play/Next/Prev)",
            "Open Application / File",
            "Open Web URL",
            "Keyboard Shortcut",
            "System Action (Screenshot/Lock/Calc/Snip)",
            "Custom Shell Command",
            "Web Search"
        ])

        type_map = {
            "window_switcher": 0,
            "app_search": 1,
            "voice_to_text": 2,
            "volume": 3,
            "media": 4,
            "open_app": 5,
            "open_url": 6,
            "keyboard": 7,
            "system": 8,
            "shell": 9,
            "web_search": 10
        }
        type_combo.setCurrentIndex(type_map.get(slot_data.get("action_type", "volume"), 3))

        detail_layout = QHBoxLayout()
        detail_input = QLineEdit(slot_data.get("action_detail", ""))
        detail_layout.addWidget(detail_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.setVisible(type_combo.currentIndex() == 5)
        detail_layout.addWidget(browse_btn)

        def on_type_changed(idx_type, slot_idx=index):
            inv_map = ["window_switcher", "app_search", "voice_to_text", "volume", "media", "open_app", "open_url", "keyboard", "system", "shell", "web_search"]
            chosen_type = inv_map[idx_type]
            self.on_slot_field_changed(slot_idx, "action_type", chosen_type)
            browse_btn.setVisible(idx_type == 5)

            if chosen_type == "window_switcher":
                detail_input.setPlaceholderText("Launches Window Switcher Task View")
            elif chosen_type == "app_search":
                detail_input.setPlaceholderText("Launches Raycast App Search Window")
            elif chosen_type == "voice_to_text":
                detail_input.setPlaceholderText("Activates Voice Typing Dictation")
            elif chosen_type == "volume":
                detail_input.setPlaceholderText("up, down, or mute")
            elif chosen_type == "media":
                detail_input.setPlaceholderText("playpause, next, or prev")
            elif chosen_type == "open_app":
                detail_input.setPlaceholderText("C:\\Windows\\notepad.exe or calc.exe")
            elif chosen_type == "open_url":
                detail_input.setPlaceholderText("https://google.com")
            elif chosen_type == "keyboard":
                detail_input.setPlaceholderText("ctrl+c, alt+tab, win+d")
            elif chosen_type == "system":
                detail_input.setPlaceholderText("screenshot, snip, lock, taskmgr, calc, notepad, explorer, settings, show_desktop")
            elif chosen_type == "shell":
                detail_input.setPlaceholderText("dir or custom batch file")
            elif chosen_type == "web_search":
                detail_input.setPlaceholderText("Search query or leaving empty")

        type_combo.currentIndexChanged.connect(on_type_changed)
        detail_input.textChanged.connect(lambda t, idx=index: self.on_slot_field_changed(idx, "action_detail", t))

        def browse_file():
            file_path, _ = QFileDialog.getOpenFileName(self, "Select Executable or File", "", "All Files (*.*)")
            if file_path:
                detail_input.setText(file_path)

        browse_btn.clicked.connect(browse_file)

        layout.addRow("Action Type:", type_combo)
        layout.addRow("Action Detail:", detail_layout)

        widget.name_input = name_input
        widget.icon_input = icon_input
        widget.detail_input = detail_input

        return widget

    def on_slot_field_changed(self, slot_idx, field, value):
        self.slots_data[slot_idx][field] = value
        if field == "name":
            self.tabs.setTabText(slot_idx, f"Slot {slot_idx+1}: {value}")
        self.wheel_preview.set_slots(self.slots_data, self.tabs.currentIndex())

    def on_tab_changed(self, index):
        self.wheel_preview.set_slots(self.slots_data, index)

    def reset_to_defaults(self):
        reply = QMessageBox.question(
            self, "Reset Defaults", "Are you sure you want to reset all slots and shortcut to default settings?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.config_data = DEFAULT_CONFIG.copy()
            self.slots_data = [dict(s) for s in self.config_data.get("slots", [])]
            self.hotkey_input.setText(self.config_data.get("hotkey", "<ctrl>+<space>"))
            self.slot_count_spin.setValue(len(self.slots_data))
            self.autostart_checkbox.setChecked(True)
            self.double_space_dot_checkbox.setChecked(False)
            self.rebuild_slot_tabs()
            self.wheel_preview.set_slots(self.slots_data, 0)

    def save_settings(self):
        self.config_data["hotkey"] = self.hotkey_input.text().strip()
        self.config_data["slots"] = self.slots_data
        is_auto = self.autostart_checkbox.isChecked()
        self.config_data["autostart"] = is_auto
        is_ds_dot = self.double_space_dot_checkbox.isChecked()
        self.config_data["double_space_dot"] = is_ds_dot

        set_autostart(is_auto)

        save_config(self.config_data)
        self.config_saved.emit(self.config_data)
        QMessageBox.information(self, "Saved", "Circle settings updated successfully!")
