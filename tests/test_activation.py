"""Activation regression tests.

These go through the real path a keypress takes — run_current(), the timer,
_invoke() — instead of calling a result's callable directly. That is exactly the
gap that once let every activation silently do nothing: the panel hid, the timer
call raised, and no console existed to show it.

Run with:  QT_QPA_PLATFORM=offscreen python tests/test_activation.py
"""

import os
import sys
import tempfile
import time
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
    cmd = "cmd"; space = "space"; backspace = "backspace"


# The search panel does not need a real keyboard hook; keep the test hermetic.
_stub("pynput")
_stub("pynput.keyboard", Controller=_Controller, Key=_Key, Listener=object,
      GlobalHotKeys=object)
_stub("pynput.mouse", Listener=object, Button=object)

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import platform_layer as platform
import theme
from search_window import SearchWindow, ROLE_HEADER, ROLE_RESULT


def spin(ms=400):
    """Pump the event loop long enough for the 70 ms activation timer."""
    done = []
    QTimer.singleShot(ms, lambda: done.append(True))
    while not done:
        QApplication.processEvents()
        time.sleep(0.01)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    theme.apply_app_theme(app)

    opened, revealed, failures = [], [], []
    platform.open_path = lambda path: (opened.append(path), True)[1]
    platform.reveal_path = lambda path: (revealed.append(path), True)[1]

    win = SearchWindow()
    indexer = getattr(win, "_indexer", None)
    if indexer is not None:
        indexer.wait(10000)

    root = tempfile.mkdtemp(prefix="circle-test-")
    spotify = os.path.join(root, "Spotify.app")
    os.makedirs(spotify, exist_ok=True)
    win.engine.apps.apps = [
        {"name": "Spotify", "path": spotify, "launch": spotify,
         "icon_source": "", "type": "bundle"},
    ]
    win.show()
    app.processEvents()

    def select(query):
        win.show()
        win.input.setText(query)
        win.refresh(query)
        app.processEvents()
        return win.list.item(win.list.currentRow()).data(ROLE_RESULT)

    # 1. Enter on an app opens it, and the panel gets out of the way.
    result = select("spot")
    assert result is not None and result.title == "Spotify", "app not found"
    win.run_current()
    assert not win.isVisible(), "panel should hide on activation"
    spin()
    assert opened == [spotify], f"app was not launched, opened={opened}"

    # 2. Shift+Enter reveals instead of opening.
    select("spot")
    win.run_current(alternate=True)
    spin()
    assert revealed == [spotify], f"reveal not called, revealed={revealed}"
    assert opened == [spotify], "reveal must not also open"

    # 3. A launch the OS refuses is reported, with the app's name.
    platform.open_path = lambda path: False
    win.action_failed.connect(lambda message: failures.append(message))
    select("spot")
    win.run_current()
    spin()
    assert len(failures) == 1, f"failure not reported: {failures}"
    assert "Spotify" in failures[0], f"failure should name the app: {failures[0]}"

    # 4. A target that no longer exists explains itself.
    platform.open_path = lambda path: True
    gone = os.path.join(root, "Gone.app")
    win.engine.apps.apps = [
        {"name": "Gone", "path": gone, "launch": gone,
         "icon_source": "", "type": "bundle"},
    ]
    failures.clear()
    select("gone")
    win.run_current()
    spin()
    assert failures and "no longer at" in failures[0], f"expected a stale-target message: {failures}"

    print("activation tests passed (4 checks)")


if __name__ == "__main__":
    main()
