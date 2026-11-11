#!/usr/bin/env bash
# Builds a drag-to-install disk image: Circle.app next to an Applications
# shortcut, in a window laid out the way macOS users expect.
#
#   ./scripts/make_dmg.sh dist/Circle.app dist/Circle-1.4.0-arm64.dmg
#
# The window layout is cosmetic and needs a Finder session, so every AppleScript
# step is allowed to fail: the disk image is still correct without it.

set -euo pipefail

APP="${1:?usage: make_dmg.sh <Circle.app> <out.dmg>}"
DMG="${2:?usage: make_dmg.sh <Circle.app> <out.dmg>}"
VOLUME="Circle"

STAGE="$(mktemp -d /tmp/circle-dmg.XXXXXX)"
RW_DMG="$(mktemp /tmp/circle-rw.XXXXXX).dmg"
MOUNT="/Volumes/${VOLUME}"

cleanup() {
  if [ -d "$MOUNT" ]; then
    hdiutil detach "$MOUNT" -quiet -force >/dev/null 2>&1 || true
  fi
  rm -rf "$STAGE" "$RW_DMG"
}
trap cleanup EXIT

echo "Staging $APP"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

# Give the icons room to breathe if the app ships a background image.
BACKGROUND=""
if [ -f "$(dirname "$0")/dmg-background.png" ]; then
  mkdir -p "$STAGE/.background"
  cp "$(dirname "$0")/dmg-background.png" "$STAGE/.background/background.png"
  BACKGROUND="yes"
fi

echo "Creating a writable image"
hdiutil create -srcfolder "$STAGE" -volname "$VOLUME" -fs HFS+ \
  -format UDRW -ov "$RW_DMG" >/dev/null

hdiutil attach "$RW_DMG" -readwrite -noverify -noautoopen >/dev/null
sleep 1

# Lay the window out. Any failure here is cosmetic.
if [ -d "$MOUNT" ]; then
  if [ -n "$BACKGROUND" ]; then
    osascript <<APPLESCRIPT >/dev/null 2>&1 || true
tell application "Finder"
  tell disk "${VOLUME}"
    open
    set current view of container window to icon view
    set toolbar visible of container window to false
    set statusbar visible of container window to false
    set the bounds of container window to {200, 160, 800, 540}
    set viewOptions to the icon view options of container window
    set arrangement of viewOptions to not arranged
    set icon size of viewOptions to 128
    set background picture of viewOptions to file ".background:background.png"
    set position of item "Circle.app" of container window to {150, 200}
    set position of item "Applications" of container window to {450, 200}
    close
  end tell
end tell
APPLESCRIPT
  else
    osascript <<APPLESCRIPT >/dev/null 2>&1 || true
tell application "Finder"
  tell disk "${VOLUME}"
    open
    set current view of container window to icon view
    set toolbar visible of container window to false
    set statusbar visible of container window to false
    set the bounds of container window to {200, 160, 800, 540}
    set viewOptions to the icon view options of container window
    set arrangement of viewOptions to not arranged
    set icon size of viewOptions to 128
    set position of item "Circle.app" of container window to {150, 200}
    set position of item "Applications" of container window to {450, 200}
    close
  end tell
end tell
APPLESCRIPT
  fi
fi

hdiutil detach "$MOUNT" -quiet -force >/dev/null 2>&1 || true

echo "Compressing"
rm -f "$DMG"
hdiutil convert "$RW_DMG" -format UDZO -imagekey zlib-level=9 -o "$DMG" >/dev/null

# Detach any copy macOS may still have mounted from the convert step.
hdiutil detach "$MOUNT" -quiet -force >/dev/null 2>&1 || true

echo "Wrote $DMG"
ls -lh "$DMG"
