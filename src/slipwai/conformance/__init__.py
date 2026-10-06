"""The conformance suite the keel exports, which a language package runs against itself.

`python -m slipwai.conformance <language-dir> <package>` from a shell, or `ConformanceCase` from a package's own
`tests/test_conformance.py`. Both run the same checks in a fresh interpreter whose package directory is the one
named, and nothing here reads the merged catalog at import, so importing the suite never loads a language.
"""
from __future__ import annotations

from .case import ConformanceCase
from .run import CHECKS, Report, check

__all__ = ["CHECKS", "ConformanceCase", "Report", "check"]
