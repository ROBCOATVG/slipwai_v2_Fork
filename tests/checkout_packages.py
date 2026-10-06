"""Pins the package directory to this checkout's `packages/`, so the suite tests the packages it pins.

Imported first by every suite that imports `slipwai`, because the merged catalogue is read at the first
`import slipwai.catalog` and this suite is `unittest`, with no `conftest.py` to run beforehand. Nothing
here imports `slipwai` until a function is called. `SLIPWAI_LANGUAGES` is set whatever the caller's
environment said, so a run is tested against the pinned package and never the person's home, and
`SLIPWAI_INDEX` is pinned to a `file:` URL that is not there, so no test reaches a network index.

`packages/` does not exist yet: the seven are pinned as submodules in slice 3.8, once the keel has the
twenty modules their import surface names. Until then `pinned()` is false and the tests that need a real
package skip with that reason rather than passing on nothing, which is the failure mode this file exists
to prevent — a suite that silently proves less than it claims.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PACKAGES = Path(__file__).resolve().parents[1] / "packages"
VARIABLE = "SLIPWAI_LANGUAGES"
# A `file:` URL that is not there, so an unreachable index is what a test meets by default.
NO_INDEX = (Path(__file__).resolve().parent / "fixtures" / "no-index").as_uri()


def unchecked(packages: Path = PACKAGES) -> list[str]:
    """A line for each package directory holding nothing: a submodule nobody initialised."""
    if not packages.is_dir():
        return []
    return [
        f"packages/{entry.name} is not checked out: git submodule update --init packages/{entry.name}"
        for entry in sorted(packages.iterdir())
        if entry.is_dir() and not entry.name.startswith(".") and not any(entry.iterdir())
    ]


def pinned(packages: Path = PACKAGES) -> bool:
    """Whether there is a package to test against at all."""
    return packages.is_dir() and any(packages.iterdir())


def pin(packages: Path = PACKAGES) -> Path:
    """Point `SLIPWAI_LANGUAGES` at `packages`, or raise the line saying one is not checked out."""
    missing = unchecked(packages)
    if missing:
        raise RuntimeError(missing[0])
    os.environ[VARIABLE] = str(packages)
    os.environ["SLIPWAI_INDEX"] = NO_INDEX
    return packages


def inside_the_command_line() -> bool:
    """Whether this process is `slipwai` itself rather than a suite: a fake package a test writes imports
    this module from inside the command the test ran against a directory and an index of its own, and
    pinning there would point the running command at the checkout halfway through."""
    spec = getattr(sys.modules.get("__main__"), "__spec__", None)
    return getattr(spec, "name", None) in ("slipwai", "slipwai.__main__")


if not inside_the_command_line():
    pin()
