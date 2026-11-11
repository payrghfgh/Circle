"""Startup behaviour: nothing is built until it is asked for.

Circle used to construct every window at launch — settings alone cost ~470 ms —
and start a file walk before anyone had searched. These checks pin down that it
no longer does.
"""

import os
import sys
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _stub(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module


class _Controller:
    def press(self, *a, **k): pass
    def release(self, *a, **k): pass
    def type(self, *a, **k): pass


class _Key:
    cmd = "cmd"; space = "space"; backspace = "backspace"; ctrl = "ctrl"
    alt = "alt"; shift = "shift"; tab = "tab"; enter = "enter"; esc = "esc"
    media_play_pause = "play"; media_next = "next"; media_previous = "prev"


_stub("pynput")
_stub("pynput.keyboard", Controller=_Controller, Key=_Key, Listener=object,
      GlobalHotKeys=object)
_stub("pynput.mouse", Listener=object, Button=object)
_stub("winreg")
_stub("pycaw")
_stub("pycaw.pycaw", AudioUtilities=object, IAudioEndpointVolume=object)
_stub("comtypes", CLSCTX_ALL=0)

from PySide6.QtWidgets import QApplication

import theme


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    theme.apply_app_theme(app)

    import main as app_main

    circle = app_main.CircleApp()

    # 1. Nothing exists yet.
    assert circle._windows == {}, f"windows built at startup: {list(circle._windows)}"

    # 2. Search is built the first time it is summoned, and only once.
    circle.show_search()
    first = circle._windows.get("search")
    assert first is not None, "search window was not created on demand"
    circle.show_search()
    assert circle._windows["search"] is first, "search window was rebuilt"

    # 3. Settings is still not built — opening Search must not drag it in.
    assert "settings" not in circle._windows, "settings built without being opened"
    assert "overlay" not in circle._windows, "wheel built without being opened"

    # 4. The wheel appears on demand too.
    circle._overlay()
    assert "overlay" in circle._windows

    # 5. Indexing starts when the panel opens, not at launch.
    assert first._indexes_started, "indexes should start on first open"

    circle.exit_app()
    print("startup tests passed (5 checks)")


if __name__ == "__main__":
    main()
