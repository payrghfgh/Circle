"""The updater must hand each machine the installer built for it.

With four assets on a release — x64 and ARM64 installers for Windows, arm64 and
x64 dmgs for macOS — picking the first matching file would give an ARM laptop
the x64 build, or the reverse.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import platform_layer as platform
import updater

ASSETS = [
    {"name": "Circle-1.5.0-setup.exe", "browser_download_url": "win-x64"},
    {"name": "Circle-1.5.0-setup-arm64.exe", "browser_download_url": "win-arm64"},
    {"name": "Circle-1.5.0-arm64.dmg", "browser_download_url": "mac-arm64"},
    {"name": "Circle-1.5.0-x64.dmg", "browser_download_url": "mac-x64"},
]


def with_machine(machine: str):
    updater.py_platform = type("P", (), {"machine": staticmethod(lambda: machine)})()


def main():
    original = (platform.IS_WINDOWS, platform.IS_MACOS)

    platform.IS_WINDOWS, platform.IS_MACOS = True, False
    with_machine("AMD64")
    assert updater.asset_for_platform(ASSETS)["browser_download_url"] == "win-x64", \
        "x64 Windows must get the x64 installer"
    with_machine("ARM64")
    assert updater.asset_for_platform(ASSETS)["browser_download_url"] == "win-arm64", \
        "ARM64 Windows must get the native ARM installer"

    platform.IS_WINDOWS, platform.IS_MACOS = False, True
    with_machine("arm64")
    assert updater.asset_for_platform(ASSETS)["browser_download_url"] == "mac-arm64"
    with_machine("x86_64")
    assert updater.asset_for_platform(ASSETS)["browser_download_url"] == "mac-x64"

    # A release from before ARM existed still updates both machines.
    old = [{"name": "Circle-1.2.0-setup.exe", "browser_download_url": "old-win"}]
    platform.IS_WINDOWS, platform.IS_MACOS = True, False
    with_machine("ARM64")
    assert updater.asset_for_platform(old)["browser_download_url"] == "old-win"

    # Nothing for this platform means no update, not a wrong download.
    platform.IS_WINDOWS, platform.IS_MACOS = False, False
    assert updater.asset_for_platform(ASSETS) is None

    platform.IS_WINDOWS, platform.IS_MACOS = original
    print("updater asset tests passed (6 checks)")


if __name__ == "__main__":
    main()
