"""This package against the conformance suite of the slipwai it is tested with (FR-030, D81).

The suite finds a package by its name in the directory above it. Where this checkout sits in a directory named for
the package (`~/.slipwai/languages/toy`, `languages/toy`), that parent is the language directory; anywhere else (a
clone called `slipwai-language-template`), the package is copied under its name into a directory of its own first,
so the suite runs from any checkout. The name is read from `language.json`, so a rename needs nothing here. Each
check is one test, failing with what is missing: `python -m slipwai.conformance <language-dir> <name>` prints the
same report.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import ClassVar

from slipwai import conformance

ROOT = Path(__file__).resolve().parents[1]
NAME = json.loads((ROOT / "language.json").read_text())["name"]


class Conformance(conformance.ConformanceCase):
    language_dir = ROOT.parent
    package = NAME
    scratch: ClassVar[tempfile.TemporaryDirectory[str] | None] = None

    @classmethod
    def setUpClass(cls) -> None:
        if ROOT.name != NAME:
            cls.scratch = tempfile.TemporaryDirectory(prefix=f"{NAME}-conformance-")
            cls.language_dir = Path(cls.scratch.name)
            shutil.copytree(ROOT, cls.language_dir / NAME, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        if cls.scratch is not None:
            cls.scratch.cleanup()
