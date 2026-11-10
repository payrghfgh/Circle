import time
import subprocess
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PySide6.QtGui import QFont, QColor
import theme
from pynput.keyboard import Controller, Key

keyboard_controller = Controller()

class VoiceTypingHUD(QWidget):
    """Sleek indicator HUD for Voice-to-Text Dictation."""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(320, 60)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel("Listening — speak now")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(theme.font(12, QFont.DemiBold))
        self.label.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(16, 16, 20, 236);
                color: {theme.TEXT};
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 18px;
                padding: 10px 18px;
            }}
        """)
        layout.addWidget(self.label)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.setInterval(4000)
        self.hide_timer.timeout.connect(self.hide)

    def trigger_voice_dictation(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - 140
        self.move(x, y)
        self.show()
        self.raise_()
        self.hide_timer.start()

        # Trigger Windows 10/11 native Voice Typing Dictation (Win + H)
        time.sleep(0.1)
        keyboard_controller.press(Key.cmd)
        keyboard_controller.press('h')
        keyboard_controller.release('h')
        keyboard_controller.release(Key.cmd)
