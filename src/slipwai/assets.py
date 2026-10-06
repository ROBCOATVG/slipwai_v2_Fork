"""Where the keel's own material lives.

Every path here is resolved from this file rather than the working directory, so `slipwai` behaves the
same whichever directory it is invoked from, and an installed or frozen command reads what is bundled into
it. Nothing in the keel reads a path any other way.

Phase 1 kept this resolution in `cli.py` because there was nowhere else for it. This is that nowhere else.
The asset trees — the toolkit, the profiles, the frontends — join it in phase 3, with the code that reads
them. There are no language or extension assets to name: those live in their packages.
"""
from __future__ import annotations

import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))
# What the wheel carries beside the package: `VERSION`, placed there by the `force-include` table in
# pyproject.toml. Absent in a checkout, where the same file sits at the repository root.
BUNDLE = Path(__file__).resolve().parent / "_bundle"
INSTALLED = BUNDLE.is_dir()
if FROZEN:
    ROOT = Path(sys._MEIPASS)  # type: ignore[attr-defined]
elif INSTALLED:
    ROOT = BUNDLE
else:
    ROOT = Path(__file__).resolve().parents[2]

# A checkout scaffolds beside itself; a command installed or frozen has no "beside", so it scaffolds where
# it is run.
DEFAULT_OUTPUT = Path.cwd() if FROZEN or INSTALLED else ROOT.parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

# Where a package is installed to, whichever kind it is. Not `languages/`, as the experiment had it: a
# directory of that name holding `codegraph` is a small lie that costs an hour later.
PACKAGES = Path.home() / ".slipwai/packages"
