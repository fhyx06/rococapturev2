# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

PROJECT_ROOT = Path(SPECPATH).resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.__about__ import APP_VERSION


a = Analysis(
    ['main.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        ('src/assets/icons', 'src/assets/icons'),
        ('src/assets/sounds', 'src/assets/sounds'),
        ('src/assets/spirits', 'src/assets/spirits'),
        ('src/assets/seasons', 'src/assets/seasons'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name=f'RocoCaptureV2-v{APP_VERSION}',
    exclude_binaries=True,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/assets/icons/app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=f'RocoCaptureV2-v{APP_VERSION}-win-x64',
)
