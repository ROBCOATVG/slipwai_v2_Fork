"""The conformance suite and the matrix, run against the package this keel holds.

A package proves itself against the keel it is built for, and the keel proves that the suite doing the
proving works. Those are different jobs and this is the second: `python -m slipwai.conformance` is run
against `packages/toy` here, on every commit, so that a package's own CI is running something known to
work rather than something nobody has tried.

The toy is inert by design — one backend, no transport, nothing to serve — which is what makes it a
fixture rather than a language. So conformance runs against it and the matrix cannot: the matrix
generates variants and runs each one's native gate, and there is nothing to run. That refusal is held
here too, because "the matrix declined to plan anything" and "the matrix planned nothing" look the same
from outside and only one of them is correct.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

import checkout_packages

from slipwai.catalog import CATALOG
from slipwai.conformance import run
from slipwai.matrix import rows

REPOSITORY = Path(__file__).resolve().parents[1]
TOY = "toy"


def entry_point(module: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    """One of the keel's `python -m` entry points, run as a package's own CI runs it."""
    return subprocess.run(
        [sys.executable, "-m", module, str(checkout_packages.PACKAGES), *arguments],
        cwd=REPOSITORY, capture_output=True, text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(REPOSITORY / "src")},
    )


class EntryPointTest(unittest.TestCase):
    def test_the_conformance_suite_runs_against_the_toy_and_reports_every_check(self) -> None:
        done = entry_point("slipwai.conformance", TOY)
        printed = done.stdout + done.stderr
        for check in ("protocol", "markers", "targets", "prune rows", "version"):
            with self.subTest(check=check):
                self.assertIn(check, printed)

    def test_those_checks_pass_for_the_toy(self) -> None:
        """The two that do not are the generation probes, which need the `generate` verb: slice 4.1."""
        printed = entry_point("slipwai.conformance", TOY).stdout
        for line in printed.splitlines():
            if line.startswith("  ") and "profiles" not in line:
                with self.subTest(line=line.strip()):
                    self.assertNotIn("FAILED", line)

    def test_a_package_the_directory_has_not_got_is_refused_rather_than_passing_empty(self) -> None:
        done = entry_point("slipwai.conformance", "a-package-nobody-wrote")
        self.assertNotEqual(done.returncode, 0)

    def test_the_matrix_plans_the_toys_variants(self) -> None:
        """Once the toy brought a transport of its own there were variants to generate, so the matrix
        plans them: the two diagonals, one per event store, and the production row."""
        done = entry_point("slipwai.matrix", TOY, "--list")
        printed = done.stdout + done.stderr
        self.assertEqual(done.returncode, 0, printed)
        for row in ("verify-standard-toy-plain-none", "verify-toy-plain-postgres",
                    "verify-production-event-modelling-toy-plain"):
            with self.subTest(row=row):
                self.assertIn(row, printed)


class RowsTest(unittest.TestCase):
    def test_a_backend_with_no_transport_has_no_variants_to_generate(self) -> None:
        """A package that serves nothing has no native gate to run, and the matrix says so rather than
        planning an empty run that passes."""
        import copy

        serves_nothing = copy.deepcopy(CATALOG)
        serves_nothing["default"]["http"] = {"toy-plain": "none"}
        with self.assertRaises(ValueError) as raised:
            rows.native_rows(serves_nothing, "toy-plain")
        self.assertIn("no variants to generate", str(raised.exception))
        self.assertIn("slipwai.conformance", str(raised.exception))

    def test_the_toy_does_have_one_now(self) -> None:
        self.assertTrue(rows.native_rows(CATALOG, "toy-plain"))

    def test_the_diagonals_still_cover_every_profile_and_frontend_the_catalogue_has(self) -> None:
        """A profile added to the catalogue and not to the diagonals is a variant nobody generates."""
        rows.covered(CATALOG)


class RunTest(unittest.TestCase):
    """A package is named by its directory name in the package directory, and by nothing else."""

    def test_a_plain_directory_name_is_accepted(self) -> None:
        run.require_package_name("toy")

    def test_a_name_that_is_a_path_is_refused(self) -> None:
        """A path would let a run reach a directory outside the one it was pointed at."""
        for bad in ("", ".", "..", "a/b", "../toy", "a\\b"):
            with self.subTest(name=bad), self.assertRaises(ValueError):
                run.require_package_name(bad)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
