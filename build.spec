# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for YouTube Transcript Downloader
# Build with: pyinstaller build.spec --noconfirm

import os
import sys
import customtkinter

block_cipher = None
is_macos = sys.platform == "darwin"

ctk_path = os.path.dirname(customtkinter.__file__)

# LITE=1 -> YouTube transcripts only: no Whisper model, no faster-whisper/ctranslate2.
LITE = os.environ.get("LITE") == "1"

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        (ctk_path, "customtkinter/"),
        ("assets", "assets"),
    ] + ([] if LITE else [("whisper_models/base", "whisper_models/base")]),
    hiddenimports=[
        "customtkinter",
        "youtube_transcript_api",
        "yt_dlp",
    ] + ([] if LITE else ["faster_whisper", "ctranslate2"]),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch",
        "torchaudio",
        "torchvision",
    ] + (["faster_whisper", "ctranslate2", "onnxruntime", "av"] if LITE else []),
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
    name="VanScript-lite" if LITE else "VanScript",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    icon="assets/icon.icns" if is_macos else "assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="VanScript-lite" if LITE else "VanScript",
)

if is_macos:
    app = BUNDLE(
        coll,
        name="VanScript.app",
        icon="assets/icon.icns",
        bundle_identifier="com.vanscript.app",
        info_plist={
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
        },
    )
