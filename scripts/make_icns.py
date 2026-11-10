"""Generate circle.icns for the macOS bundle.

Draws the Circle mark at every size macOS asks for and packs the PNGs into an
ICNS container, so the repo ships a real icon instead of a placeholder.

    python scripts/make_icns.py
"""

import os
import struct
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QBuffer, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen

SIZES = [
    ("icp4", 16), ("icp5", 32), ("icp6", 64),
    ("ic07", 128), ("ic08", 256), ("ic09", 512), ("ic10", 1024),
]

BG = QColor("#101014")
RING = QColor("#EDEDF2")
CORE = QColor("#8AB4FF")


def draw_mark(size: int) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)

    # macOS icons sit inside a rounded square with a little breathing room.
    inset = size * 0.08
    body = QRectF(inset, inset, size - inset * 2, size - inset * 2)
    painter.setPen(Qt.NoPen)
    painter.setBrush(BG)
    painter.drawRoundedRect(body, size * 0.22, size * 0.22)

    # Ring
    ring_width = max(1.0, size * 0.045)
    margin = size * 0.26
    painter.setBrush(Qt.NoBrush)
    pen = QPen(RING)
    pen.setWidthF(ring_width)
    painter.setPen(pen)
    painter.drawEllipse(QRectF(margin, margin, size - margin * 2, size - margin * 2))

    # Core
    core = size * 0.16
    painter.setPen(Qt.NoPen)
    painter.setBrush(CORE)
    painter.drawEllipse(QRectF((size - core) / 2, (size - core) / 2, core, core))

    painter.end()
    return image


def png_bytes(image: QImage) -> bytes:
    # QBuffer owns its own byte array here: wrapping a temporary QByteArray
    # leaves a dangling reference and segfaults on save.
    buffer = QBuffer()
    buffer.open(QBuffer.WriteOnly)
    image.save(buffer, "PNG")
    data = bytes(buffer.data())
    buffer.close()
    return data


def build_icns(out_path: str):
    chunks = b""
    for kind, size in SIZES:
        payload = png_bytes(draw_mark(size))
        chunks += kind.encode("ascii") + struct.pack(">I", len(payload) + 8) + payload

    total = len(chunks) + 8
    with open(out_path, "wb") as fh:
        fh.write(b"icns" + struct.pack(">I", total) + chunks)
    print(f"wrote {out_path} ({total} bytes, {len(SIZES)} sizes)")


def main():
    QGuiApplication(sys.argv)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build_icns(os.path.join(root, "circle.icns"))


if __name__ == "__main__":
    main()
