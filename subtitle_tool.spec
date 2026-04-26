# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata


block_cipher = None

datas = [
    ("assets/app_icon.ico", "assets"),
]
datas += collect_data_files("customtkinter")
datas += collect_data_files("faster_whisper", includes=["assets/*"])

hiddenimports = []
for package in (
    "faster_whisper",
    "ctranslate2",
    "av",
    "tokenizers",
):
    hiddenimports += collect_submodules(package)

hiddenimports += [
    "onnxruntime",
    "onnxruntime.capi.onnxruntime_pybind11_state",
]

for package in (
    "customtkinter",
    "faster-whisper",
    "ctranslate2",
    "av",
    "onnxruntime",
    "tokenizers",
    "huggingface-hub",
):
    try:
        datas += copy_metadata(package)
    except Exception:
        pass

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SubtitleTool",
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
    icon="assets/app_icon.ico",
)
