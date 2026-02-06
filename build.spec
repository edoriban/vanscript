# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for YouTube Transcript Downloader
# Build with: pyinstaller build.spec --noconfirm

import os
import customtkinter

block_cipher = None

ctk_path = os.path.dirname(customtkinter.__file__)

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        (ctk_path, "customtkinter/"),
        ("whisper_models/base", "whisper_models/base"),
    ],
    hiddenimports=[
        "customtkinter",
        "youtube_transcript_api",
        "yt_dlp",
        "faster_whisper",
        "ctranslate2",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch",
        "torchaudio",
        "torchvision",
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
    name="VanScript",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    # icon="assets/icon.ico",  # Uncomment if you add an icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="VanScript",
)
