import math
from PySide6.QtCore import Qt, QPoint, QRectF, Signal, QPointF, QTimer
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QCursor, QRegion, QIcon
)
from action_executor import execute_slot_action, set_system_volume_change, get_system_volume, set_system_volume_percent

class WheelOverlay(QWidget):
    action_triggered = Signal(dict)
    closed = Signal()

    def __init__(self, config_data):
        super().__init__()
        self.config_data = config_data
        self.slots = config_data.get("slots", [])
        
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setMouseTracking(True)

        self.outer_radius = self.config_data.get("theme", {}).get("radius", 150)
        self.inner_radius = self.config_data.get("theme", {}).get("inner_radius", 45)
        self.window_size = (self.outer_radius + 40) * 2
        self.resize(self.window_size, self.window_size)
        self.center_pt = QPointF(self.window_size / 2.0, self.window_size / 2.0)

        self.hovered_slot_index = -1
        self.center_hovered = False

        # Volume adjustment timer: 40ms interval for smooth +2 / -2 step hold
        self.current_volume = get_system_volume()
        self.show_volume_bar = False
        self.volume_timer = QTimer(self)
        self.volume_timer.setInterval(40)  # Ultra-smooth 40ms tick rate
        self.volume_timer.timeout.connect(self.on_volume_timer_tick)
        self.active_volume_action = None
        self.is_holding = False

        # Auto-hide volume bar timer
        self.vol_hide_timer = QTimer(self)
        self.vol_hide_timer.setSingleShot(True)
        self.vol_hide_timer.setInterval(1500)
        self.vol_hide_timer.timeout.connect(self.hide_vol_bar)

    def update_config(self, config_data):
        self.config_data = config_data
        self.slots = config_data.get("slots", [])
        self.outer_radius = self.config_data.get("theme", {}).get("radius", 150)
        self.inner_radius = self.config_data.get("theme", {}).get("inner_radius", 45)
        self.window_size = (self.outer_radius + 40) * 2
        self.resize(self.window_size, self.window_size)
        self.center_pt = QPointF(self.window_size / 2.0, self.window_size / 2.0)
        self.update()

    def show_at_cursor(self):
        cursor_pos = QCursor.pos()
        x = cursor_pos.x() - int(self.window_size / 2)
        y = cursor_pos.y() - int(self.window_size / 2)
        self.move(x, y)
        self.hovered_slot_index = -1
        self.center_hovered = True
        self.show_volume_bar = False
        self.current_volume = get_system_volume()
        self.show()
        self.raise_()
        self.activateWindow()

    def hide_vol_bar(self):
        self.show_volume_bar = False
        self.update()

    def on_volume_timer_tick(self):
        if self.active_volume_action == "up":
            self.current_volume = set_system_volume_change(2)
        elif self.active_volume_action == "down":
            self.current_volume = set_system_volume_change(-2)
        self.show_volume_bar = True
        self.vol_hide_timer.start()
        self.update()

    def wheelEvent(self, event):
        """Mouse wheel scrolling adjusts system volume live in steps of 2."""
        delta = event.angleDelta().y()
        if delta > 0:
            self.current_volume = set_system_volume_change(2)
        else:
            self.current_volume = set_system_volume_change(-2)
        self.show_volume_bar = True
        self.vol_hide_timer.start()
        self.update()

    def mouseMoveEvent(self, event):
        pos = event.position()
        dx = pos.x() - self.center_pt.x()
        dy = pos.y() - self.center_pt.y()
        dist = math.hypot(dx, dy)

        if dist < self.inner_radius:
            self.hovered_slot_index = -1
            self.center_hovered = True
        elif dist > self.outer_radius + 20:
            self.hovered_slot_index = -1
            self.center_hovered = False
        else:
            self.center_hovered = False
            angle = math.degrees(math.atan2(dy, dx))
            angle = (angle + 90) % 360
            num_slots = max(1, len(self.slots))
            span = 360.0 / num_slots
            idx = int(angle // span) % num_slots
            self.hovered_slot_index = idx

        # Drag volume bar horizontally when dragging mouse
        if event.buttons() & Qt.LeftButton and self.is_holding and self.show_volume_bar:
            bar_w = self.outer_radius * 2
            rel_x = pos.x() - (self.center_pt.x() - self.outer_radius)
            pct = max(0, min(100, int((rel_x / bar_w) * 100)))
            self.current_volume = set_system_volume_percent(pct)

        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_holding = True
            if self.hovered_slot_index != -1 and self.hovered_slot_index < len(self.slots):
                selected_slot = self.slots[self.hovered_slot_index]
                action_type = selected_slot.get("action_type", "")
                detail = selected_slot.get("action_detail", "")

                if action_type == "volume":
                    self.show_volume_bar = True
                    self.active_volume_action = detail
                    if detail in ["up", "down"]:
                        self.on_volume_timer_tick()
                        self.volume_timer.start()
                    elif detail == "mute":
                        execute_slot_action(selected_slot)
                        self.current_volume = get_system_volume()
                        self.vol_hide_timer.start()
                        self.update()
                else:
                    self.hide()
                    execute_slot_action(selected_slot)
                    self.action_triggered.emit(selected_slot)

            elif self.center_hovered:
                self.hide()
            else:
                self.hide()
        elif event.button() == Qt.RightButton:
            self.hide()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_holding = False
            if self.volume_timer.isActive():
                self.volume_timer.stop()
                self.active_volume_action = None
                self.vol_hide_timer.start()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        num_slots = max(1, len(self.slots))
        span_angle = 360.0 / num_slots

        rect_outer = QRectF(
            self.center_pt.x() - self.outer_radius,
            self.center_pt.y() - self.outer_radius,
            self.outer_radius * 2,
            self.outer_radius * 2
        )

        rect_inner = QRectF(
            self.center_pt.x() - self.inner_radius,
            self.center_pt.y() - self.inner_radius,
            self.inner_radius * 2,
            self.inner_radius * 2
        )

        bg_dark = QColor(24, 24, 37, 220)
        border_pen = QPen(QColor(255, 255, 255, 40), 1.5)
        active_border_pen = QPen(QColor(137, 180, 250, 255), 2.5)

        for i, slot in enumerate(self.slots):
            start_deg = 90 - (i * span_angle)
            end_deg = 90 - ((i + 1) * span_angle)

            path = QPainterPath()
            path.arcMoveTo(rect_outer, start_deg)
            path.arcTo(rect_outer, start_deg, -span_angle)
            path.arcTo(rect_inner, end_deg, span_angle)
            path.closeSubpath()

            is_hovered = (i == self.hovered_slot_index)
            slot_color_str = slot.get("color", "#89B4FA")
            slot_accent = QColor(slot_color_str)

            if is_hovered:
                fill_color = QColor(slot_accent.red(), slot_accent.green(), slot_accent.blue(), 185)
                painter.setBrush(QBrush(fill_color))
                painter.setPen(active_border_pen)
            else:
                painter.setBrush(QBrush(bg_dark))
                painter.setPen(border_pen)

            painter.drawPath(path)

            mid_deg = (start_deg + end_deg) / 2.0
            mid_rad = math.radians(mid_deg)
            label_radius = (self.inner_radius + self.outer_radius) / 2.0
            
            lx = self.center_pt.x() + label_radius * math.cos(mid_rad)
            ly = self.center_pt.y() - label_radius * math.sin(mid_rad)

            icon_str = slot.get("icon", "★")
            name_str = slot.get("name", f"Slot {i+1}")

            painter.setPen(QColor(255, 255, 255) if is_hovered else QColor(205, 214, 244))

            font_icon = QFont("Segoe UI Emoji", 16, QFont.Bold)
            painter.setFont(font_icon)
            painter.drawText(
                QRectF(lx - 40, ly - 22, 80, 24),
                Qt.AlignCenter,
                icon_str
            )

            font_text = QFont("Segoe UI", 8, QFont.DemiBold)
            painter.setFont(font_text)
            painter.drawText(
                QRectF(lx - 55, ly + 4, 110, 20),
                Qt.AlignCenter,
                name_str
            )

        # Center Hub
        center_path = QPainterPath()
        center_path.addEllipse(rect_inner)

        if self.center_hovered:
            painter.setBrush(QBrush(QColor(49, 50, 68, 240)))
            painter.setPen(QPen(QColor(243, 139, 168, 200), 2))
        else:
            painter.setBrush(QBrush(QColor(30, 30, 46, 230)))
            painter.setPen(border_pen)

        painter.drawPath(center_path)

        if self.show_volume_bar:
            center_title = f"{self.current_volume}%"
            center_sub = "VOLUME"
            color = QColor("#A6E3A1")
        elif self.hovered_slot_index != -1 and self.hovered_slot_index < len(self.slots):
            curr_slot = self.slots[self.hovered_slot_index]
            center_title = curr_slot.get("name", "")
            center_sub = curr_slot.get("action_type", "").upper()
            color = QColor(curr_slot.get("color", "#89B4FA"))
        elif self.center_hovered:
            center_title = "Cancel"
            center_sub = "Click to close"
            color = QColor("#F38BA8")
        else:
            center_title = "CIRCLE"
            center_sub = f"{num_slots} Slots"
            color = QColor("#89B4FA")

        painter.setPen(color)
        font_c1 = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(font_c1)
        painter.drawText(
            QRectF(self.center_pt.x() - 40, self.center_pt.y() - 14, 80, 18),
            Qt.AlignCenter,
            center_title
        )

        painter.setPen(QColor(166, 173, 200))
        font_c2 = QFont("Segoe UI", 7, QFont.Normal)
        painter.setFont(font_c2)
        painter.drawText(
            QRectF(self.center_pt.x() - 40, self.center_pt.y() + 4, 80, 14),
            Qt.AlignCenter,
            center_sub
        )

        # Volume Bar HUD
        if self.show_volume_bar:
            bar_w = self.outer_radius * 2
            bar_h = 24
            bar_x = self.center_pt.x() - (bar_w / 2)
            bar_y = self.center_pt.y() - self.outer_radius - 36

            bar_rect = QRectF(bar_x, bar_y, bar_w, bar_h)
            bg_path = QPainterPath()
            bg_path.addRoundedRect(bar_rect, 12, 12)
            painter.setBrush(QBrush(QColor(17, 17, 27, 230)))
            painter.setPen(QPen(QColor(137, 180, 250), 1.5))
            painter.drawPath(bg_path)

            fill_w = max(0.0, (self.current_volume / 100.0) * bar_w)
            if fill_w > 0:
                fill_rect = QRectF(bar_x, bar_y, fill_w, bar_h)
                fill_path = QPainterPath()
                fill_path.addRoundedRect(fill_rect, 12, 12)
                painter.setBrush(QBrush(QColor(166, 227, 161, 220)))
                painter.setPen(Qt.NoPen)
                painter.drawPath(fill_path)

            vol_icon = "🔊" if self.current_volume > 50 else ("🔉" if self.current_volume > 0 else "🔇")
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(
                bar_rect,
                Qt.AlignCenter,
                f"{vol_icon} Volume: {self.current_volume}%  (Holding +/- 2%)"
            )
