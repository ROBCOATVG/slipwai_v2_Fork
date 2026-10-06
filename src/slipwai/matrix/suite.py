"""Find a package's matrix cases and opt them in: what the command line and the root shims both run.

A package's own `tests/test_matrix.py` is loaded from its file under a name of its own (`slipwai_matrix_<package>`),
so six packages' modules of one name never shadow each other or a module of the caller's, and every `MatrixCase`
subclass in it that names this package is run — its rows only that package has included. A package with no such
module is run with a plain case. Either way the class run is a subclass over the one found, with `opted_in` set, the
package directory the one named and `only` the backends this run covers, so the package's own class, collected by
its own tests, still skips unless `SLIPWAI_MATRIX=1`.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType

from ..conformance.run import require_package_name
from .case import IMAGE_TEST, MatrixCase

MODULE = Path("tests/test_matrix.py")


def load(path: Path, package: str) -> ModuleType:
    """The module at `path`, imported under a name that is this package's alone."""
    name = f"slipwai_matrix_{package.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{path} cannot be imported")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # the matrix never writes into the package it runs, nor what that imports
    try:
        spec.loader.exec_module(module)
    except KeyboardInterrupt:
        del sys.modules[name]
        raise
    except BaseException as error:  # whatever a package's module raises, exit included, is its line, never a traceback
        del sys.modules[name]
        said = str(error) if isinstance(error, Exception) else f"it exited ({type(error).__name__}: {error})"
        raise RuntimeError(f"{path} does not import: {said}") from error
    finally:
        sys.dont_write_bytecode = previous
    return module


def cases(language_dir: Path | str, package: str, only: frozenset[str] | None = None) -> list[type[MatrixCase]]:
    """`package`'s matrix cases in `language_dir`, opted in and restricted to `only` where it is given."""
    require_package_name(package)
    directory = Path(language_dir).resolve()
    path = directory / package / MODULE
    found: list[type[MatrixCase]] = []
    if path.is_file():
        found = [value for value in vars(load(path, package)).values()
                 if isinstance(value, type) and issubclass(value, MatrixCase) and value is not MatrixCase
                 and value.package == package]
    if not found:
        found = [type("Matrix", (MatrixCase,), {"package": package, "__module__": f"slipwai_matrix_{package}"})]
    return [type(case.__name__, (case,), {"language_dir": directory, "opted_in": True, "only": only,
                                          "__module__": case.__module__, "__qualname__": case.__qualname__})
            for case in found]


def suite(found: list[type[MatrixCase]], images: bool | None = None) -> unittest.TestSuite:
    """Every test of the cases `found`: all of them, only the image test (`images=True`), or all but it (`False`)."""
    loader = unittest.TestLoader()
    tests = unittest.TestSuite()
    for case in found:
        names = [name for name in loader.getTestCaseNames(case)
                 if images is None or (name == IMAGE_TEST) == images]
        tests.addTests(case(name) for name in names)
    return tests
