"""The Search panel — Circle's answer to Spotlight.

A single field, one list, keyboard all the way through. No entrance animation:
this window is opened hundreds of times a day and anything that delays the
first character feels broken.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QKeySequence, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QStyledItemDelegate, QStyle, QVBoxLayout, QWidget,
)

import icons
import platform_layer as platform
import theme
from search_providers import Result, SearchEngine

ROLE_RESULT = Qt.UserRole + 1
ROLE_HEADER = Qt.UserRole + 2

ROW_HEIGHT = 46
HEADER_HEIGHT = 30
PANEL_WIDTH = 720
MAX_LIST_HEIGHT = 462


def _activate_app():
    """A Qt.Tool window cannot become key on macOS until the app is frontmost."""
    try:
        from AppKit import NSApp
        NSApp.activateIgnoringOtherApps_(True)
    except Exception:
        pass


class ResultDelegate(QStyledItemDelegate):
    """Paints section labels and result rows in one pass."""

    def sizeHint(self, option, index):
        if index.data(ROLE_HEADER):
            return QSize(option.rect.width(), HEADER_HEIGHT)
        return QSize(option.rect.width(), ROW_HEIGHT)

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = option.rect
        if index.data(ROLE_HEADER):
            self._paint_header(painter, rect, index.data(ROLE_HEADER))
            painter.restore()
            return

        result: Result = index.data(ROLE_RESULT)
        if result is None:
            painter.restore()
            return

        selected = bool(option.state & QStyle.State_Selected)

        if selected:
            body = QRect(rect.left() + 8, rect.top() + 2, rect.width() - 16, rect.height() - 4)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(theme.SURFACE_HI))
            painter.drawRoundedRect(body, 10, 10)

        icon_rect = QRect(rect.left() + 20, rect.top() + (rect.height() - 22) // 2, 22, 22)
        self._paint_icon(painter, icon_rect, result, selected)

        text_left = icon_rect.right() + 14
        hint = result.alt_hint if selected else ""
        right_pad = 20 + (self._hint_width(hint) if hint else 0)

        title_font = theme.font(13, QFont.DemiBold)
        painter.setFont(title_font)
        metrics = painter.fontMetrics()
        available = rect.right() - right_pad - text_left
        title = metrics.elidedText(result.title, Qt.ElideRight, max(60, available))
        title_w = metrics.horizontalAdvance(title)

        painter.setPen(QColor(theme.TEXT))
        painter.drawText(
            QRect(text_left, rect.top(), title_w + 2, rect.height()),
            Qt.AlignVCenter | Qt.AlignLeft, title,
        )

        if result.subtitle:
            sub_left = text_left + title_w + 10
            sub_width = rect.right() - right_pad - sub_left
            if sub_width > 40:
                painter.setFont(theme.font(11, QFont.Normal))
                sub_metrics = painter.fontMetrics()
                sub = sub_metrics.elidedText(result.subtitle, Qt.ElideMiddle, sub_width)
                painter.setPen(QColor(theme.TEXT_DIM))
                painter.drawText(
                    QRect(sub_left, rect.top(), sub_width, rect.height()),
                    Qt.AlignVCenter | Qt.AlignLeft, sub,
                )

        if hint:
            painter.setFont(theme.font(11, QFont.Medium))
            painter.setPen(QColor(theme.TEXT_DIM))
            painter.drawText(
                QRect(rect.right() - 20 - 90, rect.top(), 90, rect.height()),
                Qt.AlignVCenter | Qt.AlignRight, hint,
            )

        painter.restore()

    @staticmethod
    def _hint_width(text: str) -> int:
        if not text:
            return 0
        from PySide6.QtGui import QFontMetrics
        return QFontMetrics(theme.font(11, QFont.Medium)).horizontalAdvance(text) + 14

    def _paint_header(self, painter: QPainter, rect: QRect, label: str):
        painter.setFont(theme.font(10, QFont.DemiBold, tracking=0.7))
        painter.setPen(QColor(theme.TEXT_DIM))
        painter.drawText(
            QRect(rect.left() + 20, rect.top(), rect.width() - 40, rect.height()),
            Qt.AlignVCenter | Qt.AlignLeft, label.upper(),
        )

    def _paint_icon(self, painter: QPainter, rect: QRect, result: Result, selected: bool):
        native: Optional[QIcon] = getattr(result, "_icon", None)
        if native is not None and not native.isNull():
            pm = native.pixmap(QSize(44, 44))
            if not pm.isNull():
                painter.drawPixmap(rect, pm)
                return
        colour = theme.ACCENT if selected else theme.TEXT_DIM
        pm = icons.pixmap(result.icon or "file", 22, colour)
        painter.drawPixmap(rect, pm)


class ResultsList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("results")
        self.setItemDelegate(ResultDelegate(self))
        self.setMouseTracking(True)
        self.setUniformItemSizes(False)
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setFocusPolicy(Qt.NoFocus)
        self.itemEntered.connect(self._on_hover)

    def _on_hover(self, item: QListWidgetItem):
        if item and not item.data(ROLE_HEADER):
            self.setCurrentItem(item)


class SearchWindow(QWidget):
    """Frameless panel: field, grouped results, key hints."""

    closed = Signal()
    action_failed = Signal(str)

    def __init__(self, engine: Optional[SearchEngine] = None):
        super().__init__()
        self.engine = engine or SearchEngine()
        self.results: List[Result] = []
        self._suppress_hide = False
        self._has_results = False

        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool |
            Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle("Search")

        self._build_ui()
        self._load_indexes()

    # ---------------------------------------------------------------- build --

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 28)
        root.setSpacing(0)

        self.panel = QFrame(self)
        self.panel.setObjectName("panel")
        theme.panel_shadow(self.panel, blur=72, y_offset=20, alpha=190)
        root.addWidget(self.panel)

        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        # -- field ----------------------------------------------------------
        field_row = QHBoxLayout()
        field_row.setContentsMargins(22, 18, 22, 16)
        field_row.setSpacing(12)

        self.glyph = QLabel()
        self.glyph.setPixmap(icons.pixmap("search", 20, theme.TEXT_DIM))
        self.glyph.setFixedSize(20, 20)
        field_row.addWidget(self.glyph, 0, Qt.AlignVCenter)

        self.input = QLineEdit()
        self.input.setObjectName("query")
        self.input.setFont(theme.font(20, QFont.Normal, display=True))
        self.input.setPlaceholderText("Search apps, files, settings and the web")
        self.input.setClearButtonEnabled(False)
        self.input.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.input.textChanged.connect(self.refresh)
        self.input.installEventFilter(self)
        field_row.addWidget(self.input, 1)

        panel_layout.addLayout(field_row)

        self.divider = QFrame()
        self.divider.setFixedHeight(1)
        self.divider.setStyleSheet(f"background: {theme.HAIRLINE};")
        panel_layout.addWidget(self.divider)

        # -- results --------------------------------------------------------
        self.list = ResultsList(self.panel)
        self.list.setFixedHeight(ROW_HEIGHT * 4)
        self.list.itemClicked.connect(lambda _item: self.activate_current())
        panel_layout.addWidget(self.list)

        self.empty = QLabel("Nothing matches that yet.")
        self.empty.setObjectName("empty")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setFont(theme.font(12))
        self.empty.setContentsMargins(0, 28, 0, 28)
        self.empty.hide()
        panel_layout.addWidget(self.empty)

        # -- footer ---------------------------------------------------------
        self.footer = QFrame()
        self.footer.setFixedHeight(34)
        footer_row = QHBoxLayout(self.footer)
        footer_row.setContentsMargins(22, 0, 22, 0)

        self.hint_label = QLabel("↑ ↓  navigate     ↵  open     shift ↵  reveal     esc  close")
        self.hint_label.setObjectName("footer")
        self.hint_label.setFont(theme.font(11))
        footer_row.addWidget(self.hint_label)
        footer_row.addStretch()

        self.count_label = QLabel("")
        self.count_label.setObjectName("footer")
        self.count_label.setFont(theme.font(11))
        footer_row.addWidget(self.count_label)

        self.footer.setStyleSheet(f"border-top: 1px solid {theme.HAIRLINE};")
        panel_layout.addWidget(self.footer)

        self.setStyleSheet(theme.search_qss())
        self.setFixedWidth(PANEL_WIDTH + 56)

    def _load_indexes(self):
        self.engine.warm()
        self._indexer = self.engine.start_file_index()
        if self._indexer is not None:
            self._indexer.finished_index.connect(self._on_index_ready)

    def _on_index_ready(self, _count: int):
        if self.isVisible():
            self.refresh(self.input.text())

    # -------------------------------------------------------------- keyboard --

    def eventFilter(self, obj, event):
        if obj is self.input and event.type() == QEvent.KeyPress:
            key = event.key()
            mods = event.modifiers()
            if key in (Qt.Key_Down, Qt.Key_Up, Qt.Key_PageDown, Qt.Key_PageUp):
                self._move(key)
                return True
            if key in (Qt.Key_Return, Qt.Key_Enter):
                if mods & Qt.ShiftModifier:
                    self.run_current(alternate=True)
                else:
                    self.run_current()
                return True
            if key == Qt.Key_Escape:
                self.dismiss()
                return True
            if Qt.Key_1 <= key <= Qt.Key_9 and mods & Qt.ControlModifier:
                self._jump(key - Qt.Key_1)
                return True
        return super().eventFilter(obj, event)

    def _move(self, key):
        count = self.list.count()
        if count == 0:
            return
        current = self.list.currentRow()
        step = 1 if key in (Qt.Key_Down, Qt.Key_PageDown) else -1
        row = current + step
        while 0 <= row < count:
            item = self.list.item(row)
            if item and not item.data(ROLE_HEADER):
                self.list.setCurrentRow(row)
                self.list.scrollToItem(item)
                return
            row += step

    def _jump(self, index: int):
        rows = [i for i in range(self.list.count())
                if not self.list.item(i).data(ROLE_HEADER)]
        if index < len(rows):
            self.list.setCurrentRow(rows[index])

    # ----------------------------------------------------------------- show --

    def show_centered(self):
        screen = QApplication.screenAt(self.cursor().pos()) or QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.adjustSize()
        width = self.width()
        height = self.height()
        x = geo.left() + (geo.width() - width) // 2
        y = geo.top() + int(geo.height() * 0.18)
        self.move(x, min(y, geo.bottom() - height - 20))

        self.input.clear()
        self.refresh("")
        self.show()
        self.raise_()
        self.activateWindow()
        if platform.IS_MACOS:
            _activate_app()
        self.input.setFocus(Qt.ShortcutFocusReason)

    def dismiss(self):
        self.input.clear()
        self.hide()
        self.closed.emit()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if not self._suppress_hide and self.isVisible():
            self.dismiss()

    # -------------------------------------------------------------- results --

    def refresh(self, text: str):
        query = text.strip()
        self.results = self.engine.search(query)
        self._render(query)

    def _render(self, query: str):
        self.list.clear()
        last_group = None

        for result in self.results:
            if result.group != last_group:
                header = QListWidgetItem()
                header.setData(ROLE_HEADER, result.group)
                header.setFlags(Qt.NoItemFlags)
                self.list.addItem(header)
                last_group = result.group

            item = QListWidgetItem()
            item.setData(ROLE_RESULT, result)
            item.setSizeHint(QSize(0, ROW_HEIGHT))
            self.list.addItem(item)

        has_results = bool(self.results)
        self._has_results = has_results
        self.list.setVisible(has_results)
        self.empty.setVisible(not has_results)
        if not has_results:
            self.empty.setText(
                "Nothing matches that yet — try @g for the web, or a sum like 18*4."
            )

        if has_results:
            for row in range(self.list.count()):
                if not self.list.item(row).data(ROLE_HEADER):
                    self.list.setCurrentRow(row)
                    break

        self.count_label.setText(
            f"{len(self.results)} result{'s' if len(self.results) != 1 else ''}"
            if has_results else ""
        )
        self._resize_to_content()

    def _resize_to_content(self):
        """Grow the panel to fit its rows, and never past the screen."""
        total = 0
        for row in range(self.list.count()):
            total += HEADER_HEIGHT if self.list.item(row).data(ROLE_HEADER) else ROW_HEIGHT

        if self._has_results:
            self.list.setFixedHeight(max(ROW_HEIGHT, min(total, MAX_LIST_HEIGHT)))
        else:
            self.list.setFixedHeight(0)

        layout = self.panel.layout()
        layout.activate()
        height = layout.sizeHint().height() + 48  # root margins

        screen = QApplication.primaryScreen()
        if screen is not None:
            ceiling = int(screen.availableGeometry().height() * 0.82)
            if height > ceiling:
                shrink = height - ceiling
                self.list.setFixedHeight(max(ROW_HEIGHT, self.list.height() - shrink))
                layout.activate()
                height = layout.sizeHint().height() + 48

        self.setFixedHeight(height)

    # ------------------------------------------------------------------ run --

    def activate_current(self):
        self.run_current()

    def run_current(self, alternate: bool = False):
        item = self.list.currentItem()
        if item is None or item.data(ROLE_HEADER):
            return
        result: Result = item.data(ROLE_RESULT)
        action = result.alt_run if (alternate and result.alt_run) else result.run
        if action is None:
            return
        self.engine.record_use(result)
        self._suppress_hide = True
        self.hide()
        # Let the panel leave the screen before the target app takes focus.
        # PySide6's singleShot takes (msec, functor) or (msec, context, functor)
        # — never extra arguments, so the callable is bound in a closure.
        QTimer.singleShot(70, self, lambda a=action, t=result.title: self._invoke(a, t))

    def _invoke(self, action, title=""):
        try:
            action()
        except Exception as exc:
            # A windowed build has no console, so a failure has to be shown.
            self.action_failed.emit(f"{title}: {exc}" if title else str(exc))
        finally:
            self._suppress_hide = False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.dismiss()
            return
        super().keyPressEvent(event)
