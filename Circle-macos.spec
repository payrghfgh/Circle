# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build for macOS.

Produces dist/Circle.app — a menu-bar app (LSUIElement) with no Dock icon, built
as a directory bundle so it opens instantly instead of unpacking Qt on launch.
"""

import os
import sys

_HERE = globals().get("SPECPATH") or os.getcwd()
sys.path.insert(0, os.path.abspath(_HERE))
from version import __version__ as APP_VERSION

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('circle.icns', '.'),
    ],
    hiddenimports=[
        'pynput.keyboard._darwin',
        'pynput.mouse._darwin',
        'Quartz',
        'AppKit',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PySide6.QtNetwork',
        'PySide6.QtQml',
        'PySide6.QtQuick',
        'PySide6.QtWebEngineCore',
        'PySide6.Qt3DCore',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Circle',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Circle',
)

app = BUNDLE(
    coll,
    name='Circle.app',
    icon='circle.icns',
    bundle_identifier='com.circle.launcher',
    version=APP_VERSION,
    info_plist={
        'CFBundleName': 'Circle',
        'CFBundleDisplayName': 'Circle',
        'CFBundleShortVersionString': APP_VERSION,
        'CFBundleVersion': APP_VERSION,
        'CFBundleIconFile': 'circle.icns',
        'LSMinimumSystemVersion': '11.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'NSSupportsAutomaticGraphicsSwitching': True,
        # Menu-bar app: no Dock icon, no app switcher entry.
        'LSUIElement': True,
        'NSHumanReadableCopyright': 'Copyright (c) 2026',
    },
)
