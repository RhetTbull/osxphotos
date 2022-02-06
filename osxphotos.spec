# -*- mode: python ; coding: utf-8 -*-
# spec file for pyinstaller
# run `pyinstaller osxphotos.spec`

import os
import importlib

pathex = os.getcwd()

# include necessary data files
datas = [
    ("osxphotos/templates/xmp_sidecar.mako", "osxphotos/templates"),
    ("osxphotos/templates/xmp_sidecar_beta.mako", "osxphotos/templates"),
    ("osxphotos/phototemplate.tx", "osxphotos"),
    ("osxphotos/phototemplate.md", "osxphotos"),
    ("osxphotos/tutorial.md", "osxphotos"),
    ("osxphotos/exiftool_filetypes.json", "osxphotos"),
]
package_imports = [["photoscript", ["photoscript.applescript"]]]
for package, files in package_imports:
    proot = os.path.dirname(importlib.import_module(package).__file__)
    datas.extend((os.path.join(proot, f), package) for f in files)

block_cipher = None

a = Analysis(
    ["cli.py"],
    pathex=[pathex],
    binaries=[],
    datas=datas,
    hiddenimports=["pkg_resources.py2_warn"],
    hookspath=[],
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
    name="osxphotos",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)
