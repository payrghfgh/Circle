"""The update prompt.

Same surface as the rest of Circle: a frameless panel with one hairline edge.
Three states — a version to offer, a download in progress, and a ready-to-restart
confirmation. Nothing installs until the primary button is pressed.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QTextBrowser, QVBoxLayout, QWidget,
)

import icons
import platform_layer as platform
import theme
import updater
from version import __version__ as CURRENT_VERSION


class UpdateDialog(QWidget):
    """Offers an update, downloads it, then offers to restart."""

    dismissed = Signal()
    NOTES_WIDTH = 512   # 560 panel - 48 of inner padding

    def __init__(self, info: updater.UpdateInfo, parent=None):
        super().__init__(parent)
        self.info = info
        self._drag_offset = None
        self._download_thread = None
        self._installer_path = ""

        self.setWindowFlags(
            Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
            Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle("Circle update")
        self.setStyleSheet(theme.dialog_qss())

        self._build()

    # ------------------------------------------------------------------ ui --

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)

        self.panel = QFrame(self)
        self.panel.setObjectName("panel")
        theme.panel_shadow(self.panel, blur=64, y_offset=18, alpha=190)
        root.addWidget(self.panel)

        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(14)

        # -- heading ------------------------------------------------------
        heading = QHBoxLayout()
        heading.setSpacing(12)

        glyph = QLabel()
        glyph.setPixmap(icons.pixmap("update", 22, theme.ACCENT))
        glyph.setFixedSize(22, 22)
        heading.addWidget(glyph, 0, Qt.AlignTop)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.title = QLabel(f"Circle {self.info.version} is available")
        self.title.setObjectName("title")
        self.title.setFont(theme.font(16, QFont.DemiBold, display=True))
        titles.addWidget(self.title)

        self.meta = QLabel(f"You have {CURRENT_VERSION}  ·  {self.info.size_mb:.0f} MB download")
        self.meta.setObjectName("meta")
        self.meta.setFont(theme.font(11))
        titles.addWidget(self.meta)
        heading.addLayout(titles, 1)

        layout.addLayout(heading)

        # -- release notes ------------------------------------------------
        self.notes = QTextBrowser()
        self.notes.setOpenExternalLinks(True)
        self.notes.setFont(theme.font(12))
        self.notes.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.notes.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.notes.document().setDocumentMargin(0)
        self.notes.document().setDefaultStyleSheet(
            f"body {{ color: {theme.TEXT_DIM}; }}"
            f"h1, h2, h3 {{ color: {theme.TEXT}; font-size: 12px; }}"
            f"li {{ margin-bottom: 4px; }}"
            f"a {{ color: {theme.ACCENT}; }}"
            f"code {{ color: {theme.TEXT}; }}"
        )
        notes_text = (self.info.notes or "").strip() or "No release notes were provided."
        self.notes.setMarkdown(notes_text)

        # Hug the notes instead of leaving a well of empty space under them.
        self.notes.document().setTextWidth(self.NOTES_WIDTH)
        content_height = int(self.notes.document().size().height())
        self.notes.setFixedHeight(max(78, min(190, content_height + 6)))
        layout.addWidget(self.notes)

        # -- progress -----------------------------------------------------
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.hide()
        layout.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("body")
        self.status.setFont(theme.font(11))
        self.status.hide()
        layout.addWidget(self.status)

        # -- buttons ------------------------------------------------------
        footer = QHBoxLayout()
        footer.setSpacing(8)

        self.notes_button = QPushButton("Release page")
        self.notes_button.setObjectName("link")
        self.notes_button.setCursor(Qt.PointingHandCursor)
        self.notes_button.clicked.connect(self._open_release_page)
        footer.addWidget(self.notes_button)
        footer.addStretch()

        self.later_button = QPushButton("Later")
        self.later_button.setCursor(Qt.PointingHandCursor)
        self.later_button.clicked.connect(self.close)
        footer.addWidget(self.later_button)

        self.primary_button = QPushButton("Download and install")
        self.primary_button.setObjectName("primary")
        self.primary_button.setCursor(Qt.PointingHandCursor)
        self.primary_button.setDefault(True)
        self.primary_button.clicked.connect(self._primary_action)
        footer.addWidget(self.primary_button)

        layout.addLayout(footer)

        self.setFixedWidth(560)

    # --------------------------------------------------------------- states --

    def _primary_action(self):
        if self._installer_path:
            self._install()
        elif self.progress.isVisible():
            return
        else:
            self._start_download()

    def _start_download(self):
        self.primary_button.setEnabled(False)
        self.primary_button.setText("Downloading…")
        self.later_button.setText("Cancel")
        self.progress.setValue(0)
        self.progress.show()
        self.status.show()
        self.status.setText(f"Downloading {self.info.asset_name}")

        self._download_thread = updater.DownloadThread(self.info, parent=self)
        self._download_thread.progress.connect(self._on_progress)
        self._download_thread.finished_ok.connect(self._on_downloaded)
        self._download_thread.failed.connect(self._on_failed)
        self._download_thread.start()

    def _on_progress(self, done: int, total: int):
        if total > 0:
            self.progress.setValue(int(done * 100 / total))
            self.status.setText(
                f"Downloading {self.info.asset_name}  ·  "
                f"{done / 1_000_000:.1f} of {total / 1_000_000:.1f} MB"
            )
        else:
            self.status.setText(f"Downloading  ·  {done / 1_000_000:.1f} MB")

    def _on_downloaded(self, path: str):
        self._installer_path = path
        self.progress.setValue(100)
        self.status.setText("Downloaded. Circle will restart to finish.")
        self.primary_button.setEnabled(True)
        self.primary_button.setText("Restart and install")
        self.later_button.setText("Later")

    def _on_failed(self, message: str):
        self.progress.hide()
        self.status.show()
        self.status.setText(message)
        self.primary_button.setEnabled(True)
        self.primary_button.setText("Try again")
        self.later_button.setText("Close")
        self._installer_path = ""

    def _install(self):
        try:
            should_quit = updater.install(self._installer_path)
        except updater.UpdateError as exc:
            self._on_failed(str(exc))
            return
        if should_quit:
            self.close()
            QApplication.quit()

    def _open_release_page(self):
        if self.info.page_url:
            platform.open_url(self.info.page_url)

    # ------------------------------------------------------------ behaviour --

    def show_centered(self):
        self.adjustSize()
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(
                geo.left() + (geo.width() - self.width()) // 2,
                geo.top() + (geo.height() - self.height()) // 3,
            )
        self.show()
        self.raise_()
        self.activateWindow()
        if platform.IS_MACOS:
            try:
                from AppKit import NSApp
                NSApp.activateIgnoringOtherApps_(True)
            except Exception:
                pass

    def stop_threads(self, timeout_ms: int = 1200):
        """Stop an in-flight download so the app can exit cleanly."""
        thread = self._download_thread
        if thread is not None and thread.isRunning():
            thread.requestInterruption()
            if not thread.wait(timeout_ms):
                thread.terminate()
                thread.wait(300)

    def closeEvent(self, event):
        self.dismissed.emit()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    # Drag the panel by its body: it has no title bar.
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None


class UpToDateDialog(QWidget):
    """The answer to a manual check that found nothing."""

    def __init__(self, version: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet(theme.dialog_qss())

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        panel = QFrame(self)
        panel.setObjectName("panel")
        theme.panel_shadow(panel, blur=56, y_offset=14, alpha=180)
        root.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        title = QLabel(f"Circle {version} is up to date")
        title.setObjectName("title")
        title.setFont(theme.font(15, QFont.DemiBold, display=True))
        layout.addWidget(title)

        body = QLabel("You are running the newest release.")
        body.setObjectName("body")
        body.setFont(theme.font(12))
        layout.addWidget(body)

        footer = QHBoxLayout()
        footer.addStretch()
        button = QPushButton("Close")
        button.setObjectName("primary")
        button.clicked.connect(self.close)
        footer.addWidget(button)
        layout.addLayout(footer)

        self.setFixedWidth(380)

    def show_centered(self):
        self.adjustSize()
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(geo.left() + (geo.width() - self.width()) // 2,
                      geo.top() + (geo.height() - self.height()) // 3)
        self.show()
        self.raise_()
        self.activateWindow()
