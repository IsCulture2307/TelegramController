# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.building.api import PYZ, EXE
from PyInstaller.building.build_main import Analysis

# 确保当前目录在系统路径中，以便正确导入version模块
sys.path.insert(0, './')
from version import __version__
try:
    from version import __version__  # 尝试从 version.py 导入
except ImportError:
    __version__ = "0.0.0"

main_script = 'main.py'

datas = [
    ('./icons', 'icons'),
]

a = Analysis(
    [main_script],
    pathex=[os.getcwd()],
    binaries=[],
    datas=datas,
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
    a.binaries,
    a.zipfiles,
    a.datas,
    name='Telegram控制器' + "_" + __version__,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
