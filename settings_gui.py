import os
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QGroupBox, QFormLayout, QFileDialog, QTabWidget,
    QColorDialog, QMessageBox, QFrame, QScrollArea, QGridLayout, QSpinBox,
    QCheckBox, QSizePolicy
)
from PySide6.QtGui import QFont, QIcon, QColor, QPainter, QBrush, QPen
import icons
import platform_layer as platform
import theme
from version import __version__ as APP_VERSION
from config import save_config, DEFAULT_CONFIG
from action_executor import set_autostart, get_autostart

PRESET_EMOJIS = ["🪟", "🚀", "🎙️", "🔊", "🔉", "🔇", "🌐", "📸", "📝", "⚙️", "📁", "🎮", "🎵", "💻", "⚡", "🔍", "🛑", "⭐", "⏯️", "⏭️", "⏮️", "🧮", "✂️", "🔒"]
ICON_CHOICES = [
    "search", "app", "file", "folder", "calc", "globe", "gear", "power",
    "terminal", "window", "image", "music", "video", "code", "lock", "camera",
    "bin", "star", "clock", "keyboard", "copy", "sheet", "text", "link",
    "wifi", "display", "sound", "update", "mail", "store", "sleep", "user",
    "privacy", "mouse", "battery", "bluetooth",
]

PRESET_COLORS = ["#8AB4FF", "#8BE0A4", "#FAB387", "#FF8095", "#CBA6F7", "#F9E2AF", "#74C7EC", "#94E2D5"]

ACTION_PRESETS = [
    {"name": "Window Switcher", "icon_name": "window", "type": "window_switcher", "detail": "", "color": "#CBA6F7"},
    {"name": "Search", "icon_name": "search", "type": "search", "detail": "", "color": "#8AB4FF"},
    {"name": "Voice-to-Text", "icon_name": "sound", "type": "voice_to_text", "detail": "", "color": "#8BE0A4"},
    {"name": "Volume Up", "icon_name": "sound", "type": "volume", "detail": "up", "color": "#8AB4FF"},
    {"name": "Volume Down", "icon_name": "sound", "type": "volume", "detail": "down", "color": "#FF8095"},
    {"name": "Mute Audio", "icon_name": "sound", "type": "volume", "detail": "mute", "color": "#F9E2AF"},
    {"name": "Play / Pause", "icon_name": "music", "type": "media", "detail": "playpause", "color": "#8BE0A4"},
    {"name": "Next Track", "icon_name": "music", "type": "media", "detail": "next", "color": "#74C7EC"},
    {"name": "Prev Track", "icon_name": "music", "type": "media", "detail": "prev", "color": "#74C7EC"},
    {"name": "Screenshot", "icon_name": "camera", "type": "system", "detail": "screenshot", "color": "#FAB387"},
    {"name": "Screen Snippet", "icon_name": "camera", "type": "system", "detail": "snip", "color": "#FAB387"},
    {"name": "Calculator", "icon_name": "calc", "type": "system", "detail": "calc", "color": "#CBA6F7"},
    {"name": "Notepad", "icon_name": "text", "type": "system", "detail": "notepad", "color": "#CBA6F7"},
    {"name": "File Explorer", "icon_name": "folder", "type": "system", "detail": "explorer", "color": "#F9E2AF"},
    {"name": "Task Manager", "icon_name": "display", "type": "system", "detail": "taskmgr", "color": "#8AB4FF"},
    {"name": "Windows Settings", "icon_name": "gear", "type": "system", "detail": "settings", "color": "#94E2D5"},
    {"name": "Lock Screen", "icon_name": "lock", "type": "system", "detail": "lock", "color": "#FF8095"},
    {"name": "Show Desktop", "icon_name": "window", "type": "system", "detail": "show_desktop", "color": "#8AB4FF"},
    {"name": "Google", "icon_name": "globe", "type": "open_url", "detail": "https://google.com", "color": "#8BE0A4"},
    {"name": "YouTube", "icon_name": "video", "type": "open_url", "detail": "https://youtube.com", "color": "#FF8095"},
    {"name": "ChatGPT", "icon_name": "globe", "type": "open_url", "detail": "https://chatgpt.com", "color": "#94E2D5"},
    {"name": "GitHub", "icon_name": "code", "type": "open_url", "detail": "https://github.com", "color": "#EDEDF2"},
    {"name": "Web Search", "icon_name": "search", "type": "web_search", "detail": "Python tutorial", "color": "#8AB4FF"},
    {"name": "Copy (Ctrl+C)", "icon_name": "copy", "type": "keyboard", "detail": "ctrl+c", "color": "#FAB387"},
    {"name": "Paste (Ctrl+V)", "icon_name": "copy", "type": "keyboard", "detail": "ctrl+v", "color": "#8BE0A4"},
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
            color_str = slot.get("color", theme.ACCENT)
            accent_color = QColor(color_str)

            if is_sel:
                tint = QColor(accent_color)
                tint.setAlpha(60)
                painter.setBrush(QBrush(tint))
                painter.setPen(QPen(accent_color, 1.6))
            else:
                painter.setBrush(QBrush(QColor(22, 22, 28, 210)))
                painter.setPen(QPen(QColor(255, 255, 255, 30), 1))

            painter.drawPath(path)

            mid_deg = (start_deg + end_deg) / 2.0
            import math
            mid_rad = math.radians(mid_deg)
            lr = (inner_r + outer_r) / 2.0
            lx = cx + lr * math.cos(mid_rad)
            ly = cy - lr * math.sin(mid_rad)

            icon_name = slot.get("icon_name", "")
            icon_size = 16 if num_slots <= 8 else 13
            if icon_name:
                colour = theme.TEXT if is_sel else theme.TEXT_DIM
                painter.drawPixmap(
                    int(lx - icon_size / 2), int(ly - icon_size / 2),
                    icons.pixmap(icon_name, icon_size, colour),
                )
            else:
                painter.setPen(theme.TEXT if is_sel else theme.TEXT_DIM)
                painter.setFont(theme.font(10 if num_slots <= 8 else 8))
                painter.drawText(int(lx - 15), int(ly - 12), 30, 24,
                                 Qt.AlignCenter, slot.get("icon", "•"))

        # Center hub
        painter.setBrush(QBrush(QColor(17, 17, 27)))
        painter.setPen(QPen(QColor(theme.ACCENT), 1.4))
        painter.drawEllipse(int(cx - inner_r), int(cy - inner_r), int(inner_r * 2), int(inner_r * 2))

        painter.setPen(Qt.white)
        font = QFont("Segoe UI", 8, QFont.Bold)
        painter.setFont(font)
        painter.drawText(int(cx - inner_r), int(cy - 10), int(inner_r * 2), 20, Qt.AlignCenter, f"{num_slots} Slots")


class SettingsWindow(QMainWindow):
    config_saved = Signal(dict)
    test_wheel_requested = Signal()
    check_updates_requested = Signal()

    def __init__(self, config_data):
        super().__init__()
        self.config_data = config_data.copy()
        self.slots_data = [dict(s) for s in self.config_data.get("slots", [])]

        self.setWindowTitle("Circle — Settings")
        self.resize(880, 640)
        self.setMinimumSize(800, 560)

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        main_widget.setObjectName("root")
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        self.setStyleSheet(theme.settings_qss())

        # Header Title
        header_layout = QHBoxLayout()
        title_label = QLabel("Circle")
        title_label.setFont(theme.font(18, QFont.DemiBold, display=True))
        header_layout.addWidget(title_label)

        subtitle_label = QLabel(f"wheel and search  ·  v{APP_VERSION}")
        subtitle_label.setFont(theme.font(12))
        subtitle_label.setStyleSheet(f"color: {theme.TEXT_MUTE};")
        header_layout.addWidget(subtitle_label, 0, Qt.AlignBottom)
        header_layout.addStretch()

        self.test_btn = QPushButton("Test wheel")
        self.test_btn.setObjectName("testBtn")
        self.test_btn.clicked.connect(lambda: self.test_wheel_requested.emit())
        header_layout.addWidget(self.test_btn)

        main_layout.addLayout(header_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        # Hotkey & Options Group
        hotkey_box = QGroupBox("Shortcuts")
        hotkey_layout = QFormLayout(hotkey_box)
        hotkey_layout.setContentsMargins(10, 14, 10, 10)

        self.hotkey_input = QLineEdit(self.config_data.get("hotkey", "<ctrl>+<space>"))
        self.hotkey_input.setPlaceholderText(
            f"e.g. {platform.format_shortcut(platform.shortcut_presets()[0][1])}, middle_click"
        )
        hotkey_layout.addRow("Shortcut:", self.hotkey_input)

        self.hotkey_preview = QLabel()
        self.hotkey_preview.setFont(theme.font(12, QFont.DemiBold))
        self.hotkey_preview.setStyleSheet(f"color: {theme.ACCENT};")
        hotkey_layout.addRow("", self.hotkey_preview)
        self._update_hotkey_preview()
        self.hotkey_input.textChanged.connect(self._update_hotkey_preview)

        preset_layout = QGridLayout()
        preset_layout.setSpacing(6)
        presets = list(platform.shortcut_presets()) + [("Middle click", "middle_click")]
        for position, (label, value) in enumerate(presets):
            button = QPushButton(label)
            button.clicked.connect(
                lambda _checked=False, v=value: self.hotkey_input.setText(v)
            )
            preset_layout.addWidget(button, position // 2, position % 2)
        hotkey_layout.addRow("Presets:", preset_layout)

        self.slot_count_spin = QSpinBox()
        self.slot_count_spin.setRange(3, 12)
        self.slot_count_spin.setValue(len(self.slots_data))
        self.slot_count_spin.setFixedWidth(80)
        self.slot_count_spin.valueChanged.connect(self.on_slot_count_changed)
        count_row = QHBoxLayout()
        count_row.addWidget(self.slot_count_spin)
        count_row.addStretch()
        hotkey_layout.addRow("Wheel slots:", count_row)

        slot_ctrl_layout = QHBoxLayout()
        btn_add_slot = QPushButton("Add slot")
        btn_add_slot.clicked.connect(self.add_slot)
        btn_rem_slot = QPushButton("Remove slot")
        btn_rem_slot.clicked.connect(self.remove_slot)
        slot_ctrl_layout.addWidget(btn_add_slot)
        slot_ctrl_layout.addWidget(btn_rem_slot)
        slot_ctrl_layout.addStretch()
        hotkey_layout.addRow("", slot_ctrl_layout)

        self.search_hotkey_input = QLineEdit(
            self.config_data.get("search_hotkey", "<alt>+<space>")
        )
        self.search_hotkey_input.setPlaceholderText(
            f"e.g. {platform.format_shortcut('<alt>+<space>')}"
        )
        hotkey_layout.addRow("Search shortcut:", self.search_hotkey_input)

        self.search_preview = QLabel()
        self.search_preview.setFont(theme.font(12, QFont.DemiBold))
        self.search_preview.setStyleSheet(f"color: {theme.ACCENT};")
        hotkey_layout.addRow("", self.search_preview)
        self._update_search_preview()
        self.search_hotkey_input.textChanged.connect(self._update_search_preview)

        search_presets = QHBoxLayout()
        for label, value in platform.shortcut_presets():
            button = QPushButton(label)
            button.clicked.connect(
                lambda _checked=False, v=value: self.search_hotkey_input.setText(v)
            )
            search_presets.addWidget(button)
        search_presets.addStretch()
        hotkey_layout.addRow("Search presets:", search_presets)

        self.index_files_checkbox = QCheckBox("Index my files for Search")
        self.index_files_checkbox.setChecked(
            self.config_data.get("search", {}).get("index_files", True)
        )
        hotkey_layout.addRow("Search scope:", self.index_files_checkbox)

        self.update_check_checkbox = QCheckBox("Check for updates automatically")
        self.update_check_checkbox.setChecked(
            self.config_data.get("updates", {}).get("auto_check", True)
        )
        hotkey_layout.addRow("Updates:", self.update_check_checkbox)

        check_row = QHBoxLayout()
        check_now_button = QPushButton("Check now")
        check_now_button.clicked.connect(self.check_updates_requested.emit)
        check_row.addWidget(check_now_button)
        check_row.addStretch()
        hotkey_layout.addRow("", check_row)

        self.autostart_checkbox = QCheckBox(
            "Start Circle at login" if platform.IS_MACOS else "Start Circle with Windows"
        )
        is_auto = self.config_data.get("autostart", True) or get_autostart()
        self.autostart_checkbox.setChecked(is_auto)
        hotkey_layout.addRow("Startup:", self.autostart_checkbox)

        self.double_space_dot_checkbox = QCheckBox("Double spacebar types a period")
        is_ds_dot = self.config_data.get("double_space_dot", False)
        self.double_space_dot_checkbox.setChecked(is_ds_dot)
        # macOS does this itself; the toggle only exists for Windows.
        if not platform.IS_MACOS:
            hotkey_layout.addRow("Mac typing:", self.double_space_dot_checkbox)

        left_col.addWidget(hotkey_box)

        # Quick Presets Gallery Box
        preset_gallery_box = QGroupBox("Action presets")
        preset_gallery_layout = QVBoxLayout(preset_gallery_box)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(140)
        scroll_content = QWidget()
        grid = QGridLayout(scroll_content)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setSpacing(6)

        for idx, item in enumerate(ACTION_PRESETS):
            pbtn = QPushButton(item["name"])
            pbtn.setIcon(QIcon(icons.pixmap(item["icon_name"], 16, theme.TEXT_DIM)))
            pbtn.setObjectName("presetBtn")
            pbtn.clicked.connect(lambda _, p=item: self.apply_action_preset(p))
            row = idx // 2
            col = idx % 2
            grid.addWidget(pbtn, row, col)

        scroll.setWidget(scroll_content)
        preset_gallery_layout.addWidget(scroll)

        left_col.addWidget(preset_gallery_box)

        # Wheel Preview Box
        preview_box = QGroupBox("Wheel preview")
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setAlignment(Qt.AlignCenter)

        self.wheel_preview = WheelPreviewWidget(self.slots_data)
        preview_layout.addWidget(self.wheel_preview)

        left_col.addWidget(preview_box)
        left_col.addStretch()

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_container = QWidget()
        left_col.setContentsMargins(0, 0, 10, 0)
        left_container.setLayout(left_col)
        left_scroll.setWidget(left_container)
        left_scroll.setMinimumWidth(430)
        left_scroll.setMaximumWidth(470)
        content_layout.addWidget(left_scroll)

        # Right Column: Dynamic Slots Customizer Tabs
        right_col = QVBoxLayout()
        slots_group = QGroupBox("Wheel slots")
        slots_layout = QVBoxLayout(slots_group)

        self.tabs = QTabWidget()
        self.rebuild_slot_tabs()

        self.tabs.currentChanged.connect(self.on_tab_changed)
        slots_layout.addWidget(self.tabs)
        right_col.addWidget(slots_group)

        content_layout.addLayout(right_col, 1)
        main_layout.addLayout(content_layout)

        # Bottom Buttons
        bottom_layout = QHBoxLayout()

        reset_btn = QPushButton("Reset to defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        bottom_layout.addWidget(reset_btn)

        bottom_layout.addStretch()

        save_btn = QPushButton("Save changes")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.save_settings)
        bottom_layout.addWidget(save_btn)

        main_layout.addLayout(bottom_layout)

    def _update_hotkey_preview(self):
        self.hotkey_preview.setText(
            platform.format_shortcut(self.hotkey_input.text())
        )

    def _update_search_preview(self):
        self.search_preview.setText(
            platform.format_shortcut(self.search_hotkey_input.text())
        )

    def apply_action_preset(self, preset_dict):
        curr_idx = self.tabs.currentIndex()
        if 0 <= curr_idx < len(self.slots_data):
            self.slots_data[curr_idx]["name"] = preset_dict["name"]
            self.slots_data[curr_idx]["icon"] = preset_dict.get("icon", "")
            self.slots_data[curr_idx]["icon_name"] = preset_dict.get("icon_name", "")
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
        icon_layout.setSpacing(4)

        icon_scroll = QScrollArea()
        icon_scroll.setFixedHeight(148)
        icon_scroll.setWidgetResizable(True)
        icon_scroll.setFrameShape(QFrame.NoFrame)
        icon_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        icon_container = QWidget()
        icon_row = QGridLayout(icon_container)
        icon_row.setContentsMargins(0, 0, 0, 0)
        icon_row.setSpacing(4)

        current_icon = slot_data.get("icon_name", "")
        icon_buttons = []

        def choose_icon(name, idx=index):
            for button in icon_buttons:
                button.setChecked(button.property("iconName") == name)
            self.on_slot_field_changed(idx, "icon_name", name)

        for name in ICON_CHOICES:
            button = QPushButton()
            button.setCheckable(True)
            button.setProperty("iconName", name)
            button.setToolTip(name.replace("_", " ").title())
            button.setIcon(QIcon(icons.pixmap(name, 16, theme.TEXT_DIM)))
            button.setIconSize(QSize(16, 16))
            button.setFixedSize(28, 28)
            button.setChecked(name == current_icon)
            button.clicked.connect(lambda _c=False, n=name: choose_icon(n))
            position = len(icon_buttons)
            icon_row.addWidget(button, position // 10, position % 10)
            icon_buttons.append(button)
        icon_scroll.setWidget(icon_container)
        icon_layout.addWidget(icon_scroll)

        layout.addRow("Icon:", icon_layout)

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
            "Search (find anything)",
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
            "search": 1,
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
            inv_map = ["window_switcher", "search", "voice_to_text", "volume", "media", "open_app", "open_url", "keyboard", "system", "shell", "web_search"]
            chosen_type = inv_map[idx_type]
            self.on_slot_field_changed(slot_idx, "action_type", chosen_type)
            browse_btn.setVisible(idx_type == 5)

            if chosen_type == "window_switcher":
                detail_input.setPlaceholderText("Launches Window Switcher Task View")
            elif chosen_type == "search":
                detail_input.setPlaceholderText("Opens the Search panel")
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

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout.addRow(spacer)

        widget.name_input = name_input
        widget.detail_input = detail_input
        widget.choose_icon = choose_icon

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
            self.search_hotkey_input.setText(self.config_data.get("search_hotkey", "<alt>+<space>"))
            self.index_files_checkbox.setChecked(True)
            self.update_check_checkbox.setChecked(True)
            self.slot_count_spin.setValue(len(self.slots_data))
            self.autostart_checkbox.setChecked(True)
            self.double_space_dot_checkbox.setChecked(False)
            self.rebuild_slot_tabs()
            self.wheel_preview.set_slots(self.slots_data, 0)

    def save_settings(self):
        self.config_data["hotkey"] = self.hotkey_input.text().strip()
        self.config_data["search_hotkey"] = (
            self.search_hotkey_input.text().strip() or "<alt>+<space>"
        )
        updates = dict(self.config_data.get("updates") or {})
        updates["auto_check"] = self.update_check_checkbox.isChecked()
        self.config_data["updates"] = updates

        search_settings = dict(self.config_data.get("search") or {})
        search_settings["index_files"] = self.index_files_checkbox.isChecked()
        self.config_data["search"] = search_settings
        self.config_data["slots"] = self.slots_data
        is_auto = self.autostart_checkbox.isChecked()
        self.config_data["autostart"] = is_auto
        is_ds_dot = self.double_space_dot_checkbox.isChecked()
        self.config_data["double_space_dot"] = is_ds_dot

        set_autostart(is_auto)

        save_config(self.config_data)
        self.config_saved.emit(self.config_data)
        QMessageBox.information(self, "Saved", "Circle settings updated successfully!")
