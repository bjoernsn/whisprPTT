# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for whispr_ptt — push-to-talk dictation."""

import os
import site

site_packages = os.path.join('.venv', 'Lib', 'site-packages')

a = Analysis(
    ['whispr_ptt.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'faster_whisper',
        'ctranslate2',
        'pyaudio',
        'pynput',
        'pynput.keyboard',
        'pynput.keyboard._win32',
        'huggingface_hub',
        'tokenizers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# Collect ctranslate2 native libraries
ct2_dir = os.path.join(site_packages, 'ctranslate2')
for f in os.listdir(ct2_dir):
    if f.endswith(('.dll', '.pyd')):
        a.binaries.append((f'ctranslate2/{f}', os.path.join(ct2_dir, f), 'BINARY'))

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='whispr',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='whispr',
)
