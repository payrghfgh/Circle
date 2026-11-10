#!/usr/bin/env bash
# Builds Circle.app and a .dmg on macOS.
#
#   ./scripts/build_macos.sh
#
# Needs Xcode command line tools (for codesign and hdiutil) and Python 3.10+.
# Output: dist/Circle-1.1.1-<arch>.dmg

set -euo pipefail

VERSION="1.1.1"
cd "$(dirname "$0")/.."

ARCH="$(uname -m)"
case "$ARCH" in
  arm64) ARCH_LABEL="arm64" ;;
  x86_64) ARCH_LABEL="x64" ;;
  *) ARCH_LABEL="$ARCH" ;;
esac

PYTHON="${PYTHON:-python3}"

echo "== Circle build for macOS ($ARCH_LABEL) =="
"$PYTHON" --version

echo
echo "[1/5] Installing build dependencies"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt pyinstaller

echo
echo "[2/5] Checking the sources compile"
"$PYTHON" -m compileall -q .

echo
echo "[3/5] Generating the icon"
"$PYTHON" scripts/make_icns.py

echo
echo "[4/5] Freezing with PyInstaller"
"$PYTHON" -m PyInstaller Circle-macos.spec --noconfirm --clean

test -d "dist/Circle.app" || { echo "dist/Circle.app was not produced"; exit 1; }

echo
echo "[5/5] Signing (ad-hoc) and packaging the disk image"
# Ad-hoc signing is required on Apple Silicon; a Developer ID certificate would
# replace "-" and remove the Gatekeeper warning.
codesign --force --deep --sign - "dist/Circle.app"
codesign --verify --deep --strict --verbose=2 "dist/Circle.app" || true

DMG="dist/Circle-${VERSION}-${ARCH_LABEL}.dmg"
rm -f "$DMG"
hdiutil create -volname "Circle" -srcfolder "dist/Circle.app" \
    -ov -format UDZO "$DMG"

echo
echo "Done."
ls -lh "$DMG"
