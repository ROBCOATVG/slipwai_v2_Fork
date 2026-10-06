"""The `toy` language package: the language template, an inert language slipwai loads from its language directory.

`LANGUAGE` is the object core's loader reads: the `toy` family and its one backend, `toy-plain`, answering every
required member of the backend protocol. Nothing it generates builds: each answer is a placeholder in the shape the
protocol fixes, for a language author to replace with their own language's. Copy the package, rename it, and replace
them one at a time with the conformance suite running (README.md).
"""
from __future__ import annotations

from .backend import LANGUAGE

__all__ = ["LANGUAGE"]
