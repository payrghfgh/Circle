"""Shortcuts must read the way each platform writes them.

'Ctrl + Space' in a macOS menu bar is a tell that nobody tested on a Mac.
"""

import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import platform_layer as platform


def as_platform(name: str):
    """Reload the platform layer as if it were running on `name`."""
    original = sys.platform
    sys.platform = name
    try:
        importlib.reload(platform)
        return platform
    finally:
        sys.platform = original


def main():
    win = as_platform("win32")
    assert win.format_shortcut("<ctrl>+<alt>+<space>") == "Ctrl + Alt + Space", \
        win.format_shortcut("<ctrl>+<alt>+<space>")
    assert win.format_shortcut("<ctrl>+k") == "Ctrl + K"
    assert win.format_shortcut("middle_click") == "Middle click"
    assert "shift" in win.footer_hints()
    assert all("Ctrl" in label or "Alt" in label for label, _ in win.shortcut_presets())

    mac = as_platform("darwin")
    assert mac.format_shortcut("<ctrl>+<alt>+<space>") == "\u2303\u2325Space", \
        mac.format_shortcut("<ctrl>+<alt>+<space>")
    assert mac.format_shortcut("<alt>+<space>") == "\u2325Space"
    assert mac.format_shortcut("<cmd>+<shift>+k") == "\u2318\u21e7K"
    assert mac.format_shortcut("middle_click") == "Middle click"

    # The legend uses the Mac glyph for shift, never the word.
    assert "\u21e7" in mac.footer_hints() and "shift" not in mac.footer_hints()

    # Presets must be usable as specs and readable as labels.
    for label, spec in mac.shortcut_presets():
        assert spec.startswith("<"), spec
        assert label and "+" not in label, f"label should use symbols: {label}"

    as_platform(sys.platform)
    print("shortcut tests passed (11 checks)")


if __name__ == "__main__":
    main()
