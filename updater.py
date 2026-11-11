"""Auto-update from GitHub Releases.

Circle ships its installers as release assets, so updating is: ask GitHub what
the latest release is, pick the asset for this platform, download it, and hand
it to the platform's installer.

Nothing installs without the user pressing a button. The automatic part is the
check, at most once a day.

Downloads and installs are refused when running from source — replacing a
checkout with a frozen bundle is never what someone wants.
"""

from __future__ import annotations

import json
import os
import platform as py_platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from PySide6.QtCore import QThread, Signal

import config
import platform_layer as platform
from version import (GITHUB_URL, RELEASES_API, __version__ as CURRENT_VERSION,
                     version_tuple)

USER_AGENT = f"Circle/{CURRENT_VERSION} (+{GITHUB_URL})"
DEFAULT_INTERVAL_HOURS = 24


class UpdateError(Exception):
    """Anything that stops an update, with a message worth showing."""


@dataclass
class UpdateInfo:
    version: str
    notes: str = ""
    page_url: str = ""
    asset_name: str = ""
    asset_url: str = ""
    asset_size: int = 0
    published: str = ""

    @property
    def size_mb(self) -> float:
        return self.asset_size / 1_000_000 if self.asset_size else 0.0


# ------------------------------------------------------------------ helpers ---

def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def is_newer(remote: str, current: str = CURRENT_VERSION) -> bool:
    return version_tuple(remote) > version_tuple(current)


def machine_arch() -> str:
    """'arm64' or 'x64', matching the names of our release assets."""
    machine = py_platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "arm64"
    return "x64"


def asset_for_platform(assets: List[dict]) -> Optional[dict]:
    """Pick the installer that belongs on this machine."""
    names = [(a.get("name") or "", a) for a in assets]

    if platform.IS_WINDOWS:
        for name, asset in names:
            if name.lower().endswith(".exe"):
                return asset
        return None

    if platform.IS_MACOS:
        dmgs = [(n, a) for n, a in names if n.lower().endswith(".dmg")]
        if not dmgs:
            return None
        wanted = machine_arch()
        for name, asset in dmgs:
            if wanted in name.lower():
                return asset
        # A single-dmg release, or a naming scheme we do not recognise.
        return dmgs[0][1]

    return None


def platform_has_updates() -> bool:
    return platform.IS_WINDOWS or platform.IS_MACOS


# -------------------------------------------------------------------- check ---

def fetch_latest_release(timeout: int = 10) -> dict:
    request = urllib.request.Request(
        RELEASES_API,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UpdateError("No releases have been published yet.") from exc
        if exc.code in (403, 429):
            raise UpdateError(
                "GitHub is rate-limiting update checks. Try again later."
            ) from exc
        raise UpdateError(f"GitHub returned {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise UpdateError(f"Could not reach GitHub: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise UpdateError("GitHub sent a reply Circle could not read.") from exc


def check_for_update(timeout: int = 10) -> Optional[UpdateInfo]:
    """Return the newer release, or None when this copy is current."""
    release = fetch_latest_release(timeout=timeout)
    if release.get("draft") or release.get("prerelease"):
        return None

    tag = release.get("tag_name") or ""
    if not is_newer(tag):
        return None

    asset = asset_for_platform(release.get("assets") or [])
    if asset is None:
        raise UpdateError(
            f"Circle {tag.lstrip('v')} is out, but there is no build for this "
            f"platform yet. You can download it from the release page."
        )

    return UpdateInfo(
        version=tag.lstrip("vV"),
        notes=release.get("body") or "",
        page_url=release.get("html_url") or GITHUB_URL,
        asset_name=asset.get("name") or "",
        asset_url=asset.get("browser_download_url") or "",
        asset_size=int(asset.get("size") or 0),
        published=release.get("published_at") or "",
    )


def should_auto_check(settings: dict) -> bool:
    updates = settings.get("updates") or {}
    if not updates.get("auto_check", True):
        return False
    interval = float(updates.get("check_interval_hours", DEFAULT_INTERVAL_HOURS)) * 3600
    last = float(updates.get("last_check", 0) or 0)
    return (time.time() - last) >= interval


def mark_checked(settings: dict):
    settings.setdefault("updates", {})["last_check"] = time.time()


# ----------------------------------------------------------------- download ---

def download(asset_url: str, asset_name: str,
             on_progress: Optional[Callable[[int, int], None]] = None,
             chunk_size: int = 262144) -> str:
    """Stream the installer to a temp file and return its path."""
    if not asset_url:
        raise UpdateError("That release has no download for this platform.")

    target_dir = os.path.join(tempfile.gettempdir(), "CircleUpdate")
    os.makedirs(target_dir, exist_ok=True)
    target = os.path.join(target_dir, asset_name or "circle-update")

    request = urllib.request.Request(asset_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response, open(target, "wb") as fh:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                fh.write(chunk)
                done += len(chunk)
                if on_progress:
                    on_progress(done, total)
    except urllib.error.URLError as exc:
        raise UpdateError(f"Download failed: {exc.reason}") from exc
    except OSError as exc:
        raise UpdateError(f"Could not save the download: {exc}") from exc

    if os.path.getsize(target) == 0:
        raise UpdateError("The download was empty. Try again.")
    return target


# ------------------------------------------------------------------ install ---

def install(installer_path: str) -> bool:
    """Hand the downloaded file to the platform's installer.

    Returns True when the app should quit so the files can be replaced.
    """
    if not is_frozen():
        raise UpdateError(
            "This is a source checkout, not an installed copy. Update with "
            "git pull instead."
        )

    if platform.IS_WINDOWS:
        return _install_windows(installer_path)
    if platform.IS_MACOS:
        return _install_macos(installer_path)
    raise UpdateError("Updates are not supported on this platform.")


def _install_windows(installer_path: str) -> bool:
    """Run the Inno Setup installer silently; it closes and reopens Circle."""
    try:
        subprocess.Popen(
            [installer_path, "/SILENT", "/CLOSEAPPLICATIONS",
             "/RESTARTAPPLICATIONS", "/NORESTART"],
            close_fds=True,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    except OSError as exc:
        raise UpdateError(f"Could not start the installer: {exc}") from exc
    return True


def current_bundle_path() -> str:
    """.../Circle.app for a frozen macOS build."""
    executable = os.path.abspath(sys.executable)
    bundle = os.path.dirname(os.path.dirname(os.path.dirname(executable)))
    return bundle if bundle.endswith(".app") else ""


MAC_UPDATE_SCRIPT = """#!/bin/bash
# Replace Circle.app with the copy inside the downloaded disk image, then reopen.
set -u
DMG="$1"
TARGET="$2"
MOUNT="$(mktemp -d /tmp/circle-update.XXXXXX)"

sleep 1.5   # let the running copy exit and release its files

if ! hdiutil attach "$DMG" -nobrowse -quiet -mountpoint "$MOUNT"; then
  echo "attach failed"
  exit 1
fi

SOURCE="$MOUNT/Circle.app"
if [ ! -d "$SOURCE" ]; then
  hdiutil detach "$MOUNT" -quiet || true
  echo "Circle.app not found in the disk image"
  exit 1
fi

rm -rf "$TARGET.new"
if ! cp -R "$SOURCE" "$TARGET.new"; then
  hdiutil detach "$MOUNT" -quiet || true
  echo "copy failed"
  exit 1
fi

rm -rf "$TARGET"
mv "$TARGET.new" "$TARGET"
hdiutil detach "$MOUNT" -quiet || true
xattr -dr com.apple.quarantine "$TARGET" 2>/dev/null || true
open "$TARGET"
"""


def _install_macos(dmg_path: str) -> bool:
    target = current_bundle_path()
    if not target:
        raise UpdateError(
            "Circle is not running from an .app bundle, so it cannot replace "
            "itself. Open the download and drag Circle to Applications."
        )
    if not os.access(os.path.dirname(target), os.W_OK):
        raise UpdateError(
            f"Circle cannot write to {os.path.dirname(target)}. Move it to "
            "your Applications folder and try again, or install the download "
            "by hand."
        )

    script_path = os.path.join(tempfile.gettempdir(), "circle-update.sh")
    try:
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(MAC_UPDATE_SCRIPT)
        os.chmod(script_path, 0o755)
        subprocess.Popen(["/bin/bash", script_path, dmg_path, target],
                         close_fds=True, start_new_session=True)
    except OSError as exc:
        raise UpdateError(f"Could not start the update: {exc}") from exc
    return True


def reveal_download(path: str):
    """Fallback when the app cannot install the update itself."""
    platform.reveal_path(path)


# ------------------------------------------------------------------ threads ---

class UpdateCheckThread(QThread):
    """Asks GitHub for the latest release without blocking the UI."""

    found = Signal(object)      # UpdateInfo
    current = Signal(str)       # version string
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            info = check_for_update()
        except UpdateError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensive
            self.failed.emit(f"Update check failed: {exc}")
            return

        if info is None:
            self.current.emit(CURRENT_VERSION)
        else:
            self.found.emit(info)


class DownloadThread(QThread):
    """Streams the installer, reporting progress."""

    progress = Signal(int, int)   # downloaded, total
    finished_ok = Signal(str)     # local path
    failed = Signal(str)

    def __init__(self, info: UpdateInfo, parent=None):
        super().__init__(parent)
        self.info = info

    def run(self):
        try:
            path = download(
                self.info.asset_url, self.info.asset_name,
                on_progress=lambda done, total: self.progress.emit(done, total),
            )
        except UpdateError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensive
            self.failed.emit(f"Download failed: {exc}")
            return
        self.finished_ok.emit(path)


def clear_downloads():
    """Remove leftovers from a previous attempt."""
    shutil.rmtree(os.path.join(tempfile.gettempdir(), "CircleUpdate"),
                  ignore_errors=True)
