"""A drawn icon set.

Every glyph here is authored geometry on a 24x24 grid with a single stroke
weight, so the launcher never falls back to emoji or a mismatched icon theme.
Filled shapes are only used for the small status dots.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

GRID = 24.0
STROKE = 1.7


def _pen(color, width=STROKE):
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _line(p, x1, y1, x2, y2):
    p.drawLine(QPointF(x1, y1), QPointF(x2, y2))


def _rrect(p, x, y, w, h, r=3.0):
    p.drawRoundedRect(QRectF(x, y, w, h), r, r)


def _path(p, *segments, close=False):
    path = QPainterPath()
    first = True
    for seg in segments:
        cmd = seg[0]
        if cmd == "M":
            path.moveTo(seg[1], seg[2])
        elif cmd == "L":
            path.lineTo(seg[1], seg[2])
        elif cmd == "Q":
            path.quadTo(seg[1], seg[2], seg[3], seg[4])
        elif cmd == "C":
            path.cubicTo(seg[1], seg[2], seg[3], seg[4], seg[5], seg[6])
        elif cmd == "A":
            # arc: cx, cy, rx, ry, start, sweep
            path.arcMoveTo(QRectF(seg[1] - seg[3], seg[2] - seg[4], seg[3] * 2, seg[4] * 2), seg[5])
            path.arcTo(QRectF(seg[1] - seg[3], seg[2] - seg[4], seg[3] * 2, seg[4] * 2), seg[5], seg[6])
        first = False
    if close:
        path.closeSubpath()
    p.drawPath(path)
    return path


def _arc(p, cx, cy, rx, ry, start, sweep):
    """A standalone arc: its own path, so it never joins the previous stroke."""
    path = QPainterPath()
    rect = QRectF(cx - rx, cy - ry, rx * 2, ry * 2)
    path.arcMoveTo(rect, start)
    path.arcTo(rect, start, sweep)
    p.drawPath(path)


# --------------------------------------------------------------- painters ---

def _search(p):
    _path(p, ("A", 10.5, 10.5, 6.2, 6.2, 0, 360))
    _line(p, 15.2, 15.2, 20.0, 20.0)


def _app(p):
    _rrect(p, 3.2, 3.2, 7.4, 7.4, 2.4)
    _rrect(p, 13.4, 3.2, 7.4, 7.4, 2.4)
    _rrect(p, 3.2, 13.4, 7.4, 7.4, 2.4)
    _rrect(p, 13.4, 13.4, 7.4, 7.4, 2.4)


def _file(p):
    _path(p, ("M", 6.0, 2.8), ("L", 14.2, 2.8), ("L", 18.4, 7.0),
          ("L", 18.4, 21.2), ("L", 6.0, 21.2), ("L", 6.0, 2.8), close=True)
    _path(p, ("M", 14.2, 2.8), ("L", 14.2, 7.0), ("L", 18.4, 7.0))


def _folder(p):
    _path(p, ("M", 3.2, 6.6), ("L", 3.2, 18.8), ("L", 20.8, 18.8),
          ("L", 20.8, 8.6), ("L", 11.6, 8.6), ("L", 9.4, 5.4),
          ("L", 3.2, 5.4), close=True)


def _calc(p):
    _rrect(p, 4.4, 2.8, 15.2, 18.4, 3.2)
    _line(p, 7.8, 7.4, 16.2, 7.4)
    for x in (8.6, 12.0, 15.4):
        for y in (12.0, 16.4):
            p.drawPoint(QPointF(x, y))


def _globe(p):
    _path(p, ("A", 12, 12, 8.6, 8.6, 0, 360))
    _path(p, ("A", 12, 12, 3.6, 8.6, 0, 360))
    _line(p, 3.4, 12, 20.6, 12)


def _gear(p):
    for y, knob in ((6.8, 15.2), (12.0, 9.0), (17.2, 13.4)):
        _line(p, 4.2, y, 19.8, y)
        _arc(p, knob, y, 2.2, 2.2, 0, 360)

def _power(p):
    _path(p, ("A", 12, 12.6, 7.2, 7.2, 130, 280))
    _line(p, 12, 2.6, 12, 11.0)


def _terminal(p):
    _rrect(p, 2.8, 4.0, 18.4, 16.0, 3.2)
    _path(p, ("M", 6.6, 9.4), ("L", 9.6, 12.0), ("L", 6.6, 14.6))
    _line(p, 12.2, 15.0, 17.0, 15.0)


def _window(p):
    _rrect(p, 2.8, 4.2, 18.4, 15.6, 3.0)
    _line(p, 2.8, 8.6, 21.2, 8.6)
    p.drawPoint(QPointF(5.6, 6.4))
    p.drawPoint(QPointF(8.2, 6.4))


def _image(p):
    _rrect(p, 3.0, 4.4, 18.0, 15.2, 3.0)
    _path(p, ("M", 4.0, 17.0), ("L", 9.4, 11.6), ("L", 14.0, 16.2),
          ("L", 16.6, 13.6), ("L", 20.4, 17.4))
    _path(p, ("A", 8.6, 9.4, 1.5, 1.5, 0, 360))


def _music(p):
    _path(p, ("M", 9.4, 17.4), ("L", 9.4, 6.2), ("L", 19.0, 4.2),
          ("L", 19.0, 15.0))
    _path(p, ("A", 7.2, 17.6, 2.2, 2.0, 0, 360))
    _path(p, ("A", 16.8, 15.2, 2.2, 2.0, 0, 360))


def _video(p):
    _rrect(p, 2.8, 5.4, 12.8, 13.2, 3.0)
    _path(p, ("M", 15.6, 10.6), ("L", 21.2, 7.4), ("L", 21.2, 16.6),
          ("L", 15.6, 13.4), close=True)


def _code(p):
    _path(p, ("M", 8.6, 7.4), ("L", 3.6, 12.0), ("L", 8.6, 16.6))
    _path(p, ("M", 15.4, 7.4), ("L", 20.4, 12.0), ("L", 15.4, 16.6))
    _line(p, 13.4, 5.2, 10.6, 18.8)


def _lock(p):
    _arc(p, 12, 8.8, 3.6, 3.6, 0, 180)
    _line(p, 8.4, 8.8, 8.4, 10.6)
    _line(p, 15.6, 8.8, 15.6, 10.6)
    _rrect(p, 4.6, 10.6, 14.8, 10.0, 2.8)

def _camera(p):
    _rrect(p, 2.8, 6.8, 18.4, 13.2, 3.2)
    _path(p, ("M", 8.6, 6.8), ("L", 10.0, 4.0), ("L", 14.0, 4.0), ("L", 15.4, 6.8))
    _path(p, ("A", 12, 13.4, 3.6, 3.6, 0, 360))


def _bin(p):
    _line(p, 4.4, 6.8, 19.6, 6.8)
    _path(p, ("M", 9.4, 6.8), ("L", 9.4, 3.8), ("L", 14.6, 3.8), ("L", 14.6, 6.8))
    _path(p, ("M", 6.6, 6.8), ("L", 7.6, 20.2), ("L", 16.4, 20.2), ("L", 17.4, 6.8))
    _line(p, 10.6, 10.4, 10.9, 16.8)
    _line(p, 13.4, 10.4, 13.1, 16.8)


def _star(p):
    _path(p, ("M", 12, 3.4), ("L", 14.6, 9.0), ("L", 20.6, 9.7),
          ("L", 16.2, 13.8), ("L", 17.4, 19.8), ("L", 12, 16.8),
          ("L", 6.6, 19.8), ("L", 7.8, 13.8), ("L", 3.4, 9.7),
          ("L", 9.4, 9.0), close=True)


def _clock(p):
    _path(p, ("A", 12, 12, 8.6, 8.6, 0, 360))
    _path(p, ("M", 12, 7.0), ("L", 12, 12.2), ("L", 15.8, 14.2))


def _keyboard(p):
    _rrect(p, 2.4, 6.6, 19.2, 11.2, 3.0)
    for x in (6.2, 9.4, 12.6, 15.8):
        p.drawPoint(QPointF(x, 10.4))
    _line(p, 7.2, 14.0, 16.8, 14.0)


def _arrow_right(p):
    _line(p, 4.4, 12, 19.2, 12)
    _path(p, ("M", 13.4, 6.4), ("L", 19.2, 12), ("L", 13.4, 17.6))


def _copy(p):
    _rrect(p, 3.8, 3.8, 11.4, 11.4, 2.6)
    _rrect(p, 8.8, 8.8, 11.4, 11.4, 2.6)

def _sheet(p):
    _rrect(p, 3.6, 4.4, 16.8, 15.2, 2.6)
    _line(p, 3.6, 9.4, 20.4, 9.4)
    _line(p, 3.6, 14.4, 20.4, 14.4)
    _line(p, 11.0, 9.4, 11.0, 19.6)


def _text(p):
    _line(p, 5.0, 6.2, 19.0, 6.2)
    _line(p, 12.0, 6.2, 12.0, 18.4)
    _line(p, 9.0, 18.4, 15.0, 18.4)


def _link(p):
    _path(p, ("M", 10.4, 13.6), ("L", 13.6, 10.4))
    _path(p, ("M", 8.8, 15.2), ("L", 6.8, 17.2),
          ("A", 6.8, 17.2, 2.6, 2.6, 180, 200))
    _path(p, ("M", 15.2, 8.8), ("L", 17.2, 6.8),
          ("A", 17.2, 6.8, 2.6, 2.6, 0, 200))


def _wifi(p):
    _arc(p, 12, 19.2, 8.8, 8.8, 28, 124)
    _arc(p, 12, 19.2, 5.4, 5.4, 28, 124)
    _arc(p, 12, 19.2, 2.0, 2.0, 0, 360)

def _display(p):
    _rrect(p, 2.8, 4.4, 18.4, 12.8, 2.6)
    _line(p, 8.4, 20.2, 15.6, 20.2)
    _line(p, 12.0, 17.2, 12.0, 20.2)


def _sound(p):
    _path(p, ("M", 4.0, 9.4), ("L", 8.0, 9.4), ("L", 12.6, 5.4),
          ("L", 12.6, 18.6), ("L", 8.0, 14.6), ("L", 4.0, 14.6), close=True)
    _path(p, ("M", 15.6, 9.0), ("A", 16.6, 12.0, 4.2, 4.2, 300, 120))


def _update(p):
    _path(p, ("A", 12, 12, 8.2, 8.2, 40, 280))
    _path(p, ("M", 17.6, 3.6), ("L", 18.6, 8.6), ("L", 13.6, 8.2))


def _mail(p):
    _rrect(p, 2.8, 5.6, 18.4, 12.8, 2.8)
    _path(p, ("M", 4.0, 7.4), ("L", 12, 13.2), ("L", 20.0, 7.4))


def _store(p):
    _path(p, ("M", 4.4, 9.4), ("L", 5.6, 4.4), ("L", 18.4, 4.4), ("L", 19.6, 9.4))
    _path(p, ("M", 4.4, 9.4), ("L", 4.4, 19.6), ("L", 19.6, 19.6), ("L", 19.6, 9.4))
    _path(p, ("M", 9.6, 19.6), ("L", 9.6, 13.6), ("L", 14.4, 13.6), ("L", 14.4, 19.6))


def _sleep(p):
    _path(p, ("A", 10.8, 12.0, 8.0, 8.0, 60, 240))
    _path(p, ("A", 15.4, 9.6, 6.6, 6.6, 105, 190))


def _user(p):
    _arc(p, 12, 8.4, 3.8, 3.8, 0, 360)
    _path(p, ("M", 5.0, 20.2), ("C", 5.0, 15.0, 19.0, 15.0, 19.0, 20.2))

def _privacy(p):
    _path(p, ("M", 12, 3.4), ("L", 19.4, 6.2), ("L", 19.4, 11.8),
          ("C", 19.4, 16.6, 15.9, 19.4, 12, 20.6),
          ("C", 8.1, 19.4, 4.6, 16.6, 4.6, 11.8),
          ("L", 4.6, 6.2), close=True)

def _mouse(p):
    _rrect(p, 7.2, 2.8, 9.6, 18.4, 4.8)
    _line(p, 12.0, 6.4, 12.0, 9.6)


def _battery(p):
    _rrect(p, 2.8, 7.6, 16.4, 8.8, 2.6)
    _line(p, 21.2, 10.6, 21.2, 13.4)
    _line(p, 6.4, 10.0, 6.4, 14.0)


def _bluetooth(p):
    _path(p, ("M", 8.4, 7.4), ("L", 15.6, 16.6), ("L", 12.0, 20.4),
          ("L", 12.0, 3.6), ("L", 15.6, 7.4), ("L", 8.4, 16.6))


def _dot(p):
    p.setBrush(QColor(p.pen().color()))
    p.drawEllipse(QRectF(9.6, 9.6, 4.8, 4.8))
    p.setBrush(Qt.NoBrush)


_PAINTERS = {
    "search": _search, "app": _app, "file": _file, "folder": _folder,
    "calc": _calc, "globe": _globe, "gear": _gear, "power": _power,
    "terminal": _terminal, "window": _window, "image": _image, "music": _music,
    "video": _video, "code": _code, "lock": _lock, "camera": _camera,
    "bin": _bin, "star": _star, "clock": _clock, "keyboard": _keyboard,
    "arrow": _arrow_right, "copy": _copy, "sheet": _sheet, "text": _text,
    "link": _link, "wifi": _wifi, "display": _display, "sound": _sound,
    "update": _update, "mail": _mail, "store": _store, "sleep": _sleep,
    "user": _user, "privacy": _privacy, "mouse": _mouse, "battery": _battery,
    "bluetooth": _bluetooth, "dot": _dot,
}

_cache = {}


def pixmap(name, size=22, color="#EDEDF2", dpr=2.0):
    key = (name, int(size), color, round(dpr, 2))
    if key in _cache:
        return _cache[key]

    painter_fn = _PAINTERS.get(name, _file)
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    # Logical units: the pixmap carries its own devicePixelRatio, so a
    # 24-unit grid maps onto `size` logical pixels and stays crisp at 2x.
    p.scale(size / GRID, size / GRID)
    p.setPen(_pen(color, STROKE * (1.0 if size >= 18 else 1.15)))
    p.setBrush(Qt.NoBrush)
    painter_fn(p)
    p.end()

    _cache[key] = pm
    return pm


def icon(name, size=22, color="#EDEDF2", dpr=2.0):
    return QIcon(pixmap(name, size, color, dpr))
