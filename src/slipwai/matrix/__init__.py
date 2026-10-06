"""A language package's own generated-variant matrix, which the keel exports for the package to run.

`python -m slipwai.matrix <language-dir> <package>` from a shell, or `MatrixCase` from a package's own
`tests/test_matrix.py`, which skips unless `SLIPWAI_MATRIX=1`. Both generate every native-gate variant of the
package's own backends and hold each to its native `make verify`, and build and start each backend's image where
Docker is here. The plan is read in a fresh interpreter whose package directory is the one named, so importing this
never loads a language.
"""
from __future__ import annotations

from .case import IMAGE_TEST, NATIVE_TEST, MatrixCase
from .rows import Row
from .run import Plan, plan

__all__ = ["IMAGE_TEST", "NATIVE_TEST", "MatrixCase", "Plan", "Row", "plan"]
