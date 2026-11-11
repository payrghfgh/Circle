"""Write installer/version_info.txt from version.py.

Keeps the Windows file-version resource in step with the app version, so the
installer, the executable and the update check never disagree.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from version import __version__

TEMPLATE = """VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, 0),
    prodvers=({major}, {minor}, {patch}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [StringStruct('CompanyName', 'Circle'),
           StringStruct('FileDescription', 'Circle - radial launcher and search'),
           StringStruct('FileVersion', '{version}.0'),
           StringStruct('InternalName', 'Circle'),
           StringStruct('LegalCopyright', 'Copyright (c) 2026'),
           StringStruct('OriginalFilename', 'Circle.exe'),
           StringStruct('ProductName', 'Circle'),
           StringStruct('ProductVersion', '{version}.0')])
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main():
    parts = [int(p) for p in __version__.split(".")[:3]]
    while len(parts) < 3:
        parts.append(0)
    major, minor, patch = parts

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "installer", "version_info.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(TEMPLATE.format(major=major, minor=minor, patch=patch,
                                 version=__version__))
    print(f"wrote {out} for {__version__}")


if __name__ == "__main__":
    main()
