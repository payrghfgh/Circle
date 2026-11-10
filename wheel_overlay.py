import math
from PySide6.QtCore import Qt, QPoint, QRectF, Signal, QPointF, QTimer
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QCursor, QRegion, QIcon
)
import icons
import theme
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

        slot_fill = QColor(22, 22, 28, 216)
        hairline = QPen(QColor(255, 255, 255, 30), 1.0)
        hairline.setCosmetic(True)

        for i, slot in enumerate(self.slots):
            start_deg = 90 - (i * span_angle)
            end_deg = 90 - ((i + 1) * span_angle)

            path = QPainterPath()
            path.arcMoveTo(rect_outer, start_deg)
            path.arcTo(rect_outer, start_deg, -span_angle)
            path.arcTo(rect_inner, end_deg, span_angle)
            path.closeSubpath()

            is_hovered = (i == self.hovered_slot_index)
            accent = QColor(slot.get("color", theme.ACCENT))

            if is_hovered:
                tint = QColor(accent)
                tint.setAlpha(48)
                painter.setBrush(QBrush(tint))
                pen = QPen(accent, 1.5)
                painter.setPen(pen)
            else:
                painter.setBrush(QBrush(slot_fill))
                painter.setPen(hairline)

            painter.drawPath(path)

            mid_deg = (start_deg + end_deg) / 2.0
            mid_rad = math.radians(mid_deg)
            label_radius = (self.inner_radius + self.outer_radius) / 2.0

            lx = self.center_pt.x() + label_radius * math.cos(mid_rad)
            ly = self.center_pt.y() - label_radius * math.sin(mid_rad)

            icon_name = slot.get("icon_name", "")
            if icon_name:
                colour = theme.TEXT if is_hovered else theme.TEXT_DIM
                glyph = icons.pixmap(icon_name, 20, colour)
                painter.drawPixmap(
                    QRectF(lx - 10, ly - 26, 20, 20), glyph,
                    QRectF(0, 0, glyph.width(), glyph.height()),
                )
            else:
                painter.setPen(QColor(theme.TEXT) if is_hovered else QColor(theme.TEXT_DIM))
                painter.setFont(theme.emoji_font(15))
                painter.drawText(QRectF(lx - 40, ly - 24, 80, 26), Qt.AlignCenter,
                                 slot.get("icon", "•"))

            painter.setPen(QColor(theme.TEXT) if is_hovered else QColor(theme.TEXT_DIM))
            painter.setFont(theme.font(9, QFont.DemiBold))
            painter.drawText(QRectF(lx - 58, ly + 4, 116, 18), Qt.AlignCenter,
                             slot.get("name", f"Slot {i + 1}"))

        # ---- centre hub ----
        centre_path = QPainterPath()
        centre_path.addEllipse(rect_inner)

        if self.center_hovered:
            painter.setBrush(QBrush(QColor(30, 30, 38, 242)))
            ring = QPen(QColor(theme.DANGER), 1.4)
        else:
            painter.setBrush(QBrush(QColor(16, 16, 20, 236)))
            ring = hairline
        painter.setPen(ring)
        painter.drawPath(centre_path)

        if self.show_volume_bar:
            centre_title = f"{self.current_volume}%"
            centre_sub = "VOLUME"
            colour = QColor(theme.OK)
        elif 0 <= self.hovered_slot_index < len(self.slots):
            current = self.slots[self.hovered_slot_index]
            centre_title = current.get("name", "")
            centre_sub = current.get("action_type", "").upper()
            colour = QColor(current.get("color", theme.ACCENT))
        elif self.center_hovered:
            centre_title = "Close"
            centre_sub = "CLICK"
            colour = QColor(theme.DANGER)
        else:
            centre_title = "Circle"
            centre_sub = f"{num_slots} SLOTS"
            colour = QColor(theme.ACCENT)

        painter.setPen(colour)
        painter.setFont(theme.font(11, QFont.DemiBold))
        painter.drawText(
            QRectF(self.center_pt.x() - 44, self.center_pt.y() - 15, 88, 18),
            Qt.AlignCenter, centre_title
        )

        painter.setPen(QColor(theme.TEXT_MUTE))
        painter.setFont(theme.font(7, QFont.DemiBold, tracking=0.8))
        painter.drawText(
            QRectF(self.center_pt.x() - 44, self.center_pt.y() + 3, 88, 14),
            Qt.AlignCenter, centre_sub
        )

        # ---- volume HUD ----
        if self.show_volume_bar:
            bar_w = self.outer_radius * 2
            bar_h = 22
            bar_x = self.center_pt.x() - (bar_w / 2)
            bar_y = self.center_pt.y() - self.outer_radius - 34

            bar_rect = QRectF(bar_x, bar_y, bar_w, bar_h)
            bg_path = QPainterPath()
            bg_path.addRoundedRect(bar_rect, 11, 11)
            painter.setBrush(QBrush(QColor(16, 16, 20, 238)))
            painter.setPen(hairline)
            painter.drawPath(bg_path)

            fill_w = max(0.0, (self.current_volume / 100.0) * bar_w)
            if fill_w > 2:
                fill_rect = QRectF(bar_x, bar_y, fill_w, bar_h)
                fill_path = QPainterPath()
                fill_path.addRoundedRect(fill_rect, 11, 11)
                painter.setBrush(QBrush(QColor(138, 180, 255, 120)))
                painter.setPen(Qt.NoPen)
                painter.drawPath(fill_path)

            painter.setPen(QColor(theme.TEXT))
            painter.setFont(theme.font(10, QFont.DemiBold))
            painter.drawText(bar_rect, Qt.AlignCenter, f"{self.current_volume}%")
