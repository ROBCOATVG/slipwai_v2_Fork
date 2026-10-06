# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


root = Path(SPECPATH)

analysis = Analysis(
    [str(root / "src/slipwai/__main__.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[
        (str(root / "assets"), "assets"),
        (str(root / "catalog.json"), "."),
        (str(root / "VERSION"), "."),
        # CHANGELOG.md and changelog.d/ are carried here in version 1, because `migrate` takes its
        # catch-up notes out of them and a frozen command has no checkout beside it. Neither exists in
        # this repository until slice 8.1 brings the release machinery, and PyInstaller fails on a
        # `datas` entry that is not there — so they are added back with them.
    ],
    # A language package is loaded from the package directory at run time and imports the keel by name,
    # so every keel module stays in the executable whether or not a static import from `__main__`
    # reaches it. The executable bundles no package: it is the keel alone, the same as the wheel, so
    # there is one artefact to build and sign and no bundled copy to drift from the chandlery's.
    hiddenimports=collect_submodules("slipwai"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="slipwai",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
