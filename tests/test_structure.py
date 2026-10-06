"""What `check-structure` refuses, proven by making it refuse.

A gate nobody has seen fail is a gate nobody knows the shape of. Each test here builds a small tree that
breaks exactly one rule and asserts the gate says so, naming the file and the reason; the last one runs the
gate against this repository, which is the only way to know the rules are satisfiable by real code.

The gate is driven by patching its module globals at the tree it should read, rather than by a subprocess,
so the whole suite stays inside the per-increment gate. `main()` reads nothing else.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY / "scripts/check-structure.py"

_spec = importlib.util.spec_from_file_location("check_structure", SCRIPT)
assert _spec is not None and _spec.loader is not None
structure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(structure)

CLEAN_TIERS = (("foundation", ("errors",)), ("edge", ("cli",)), ("package", ("__init__",)))


def run_gate(
    root: Path,
    modules: dict[str, str],
    *,
    tiers: tuple[tuple[str, tuple[str, ...]], ...] = CLEAN_TIERS,
    surface: str = "",
    packages: dict[str, str] | None = None,
    suites: dict[str, str] | None = None,
) -> tuple[int, str]:
    """Write a tree and run the gate over it, returning its exit code and what it printed to stderr."""
    keel = root / "src/slipwai"
    for name, text in modules.items():
        path = keel / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (root / "tests").mkdir(exist_ok=True)
    for name, text in (suites or {}).items():
        (root / "tests" / name).write_text(text, encoding="utf-8")
    for name, text in (packages or {}).items():
        path = root / "packages" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (root / "import-surface.txt").write_text(surface, encoding="utf-8")

    stderr = io.StringIO()
    with mock.patch.multiple(
        structure, ROOT=root, KEEL=keel, PACKAGES=root / "packages", SURFACE=root / "import-surface.txt", TIERS=tiers
    ), contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
        code = structure.main()
    return code, stderr.getvalue()


class GateTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def gate(self, modules: dict[str, str], **options: Any) -> tuple[int, str]:
        return run_gate(self.root, modules, **options)

    def test_a_tree_that_keeps_every_rule_passes(self) -> None:
        code, said = self.gate({"__init__.py": '"""The keel."""\n', "errors.py": '"""A refusal."""\n'})
        self.assertEqual((code, said), (0, ""))

    def test_an_import_against_the_direction_is_refused(self) -> None:
        """`errors` is inward of `cli`, so it may not read it. This is the rule the gate exists for."""
        code, said = self.gate({
            "__init__.py": '"""The keel."""\n',
            "cli.py": '"""The command line."""\n',
            "errors.py": '"""A refusal."""\nfrom .cli import main\n',
        })
        self.assertEqual(code, 1)
        self.assertIn("foundation imports edge: errors -> cli", said)
        self.assertIn("Imports point inward", said)

    def test_the_same_import_the_other_way_round_is_allowed(self) -> None:
        """Outward may read inward; that is the whole point of the direction having one."""
        code, said = self.gate({
            "__init__.py": '"""The keel."""\n',
            "errors.py": '"""A refusal."""\n',
            "cli.py": '"""The command line."""\nfrom .errors import *  # noqa: F403\n',
        })
        self.assertEqual((code, said), (0, ""))

    def test_a_cycle_is_named_rather_than_left_to_become_an_import_error(self) -> None:
        code, said = self.gate(
            {
                "__init__.py": '"""The keel."""\n',
                "a.py": '"""A."""\nfrom .b import thing\n',
                "b.py": '"""B."""\nfrom .a import other\n',
            },
            tiers=(("foundation", ("a", "b")), ("package", ("__init__",))),
        )
        self.assertEqual(code, 1)
        self.assertIn("import cycle:", said)

    def test_a_module_over_the_budget_is_refused(self) -> None:
        body = "\n".join(f"x{n} = {n}" for n in range(structure.MODULE_BUDGET + 1))
        code, said = self.gate({"__init__.py": '"""The keel."""\n', "errors.py": f'"""A refusal."""\n{body}\n'})
        self.assertEqual(code, 1)
        self.assertIn(f"over the {structure.MODULE_BUDGET}-line budget", said)

    def test_a_facade_that_does_more_than_dispatch_is_refused(self) -> None:
        body = "\n".join(f"x{n} = {n}" for n in range(structure.FACADE_BUDGET + 1))
        code, said = self.gate({"__init__.py": f'"""The keel."""\n{body}\n'})
        self.assertEqual(code, 1)
        self.assertIn("package facade", said)

    def test_a_module_with_no_docstring_is_refused(self) -> None:
        code, said = self.gate({"__init__.py": '"""The keel."""\n', "errors.py": "THING = 1\n"})
        self.assertEqual(code, 1)
        self.assertIn("no module docstring saying what part this is", said)

    def test_a_module_in_no_tier_stops_the_gate_rather_than_passing_unchecked(self) -> None:
        """Silence here would let a module arrive with no declared place, which is how tiers rot."""
        with self.assertRaises(SystemExit) as raised:
            self.gate({"__init__.py": '"""The keel."""\n', "stowaway.py": '"""Nowhere."""\n'})
        self.assertIn("belongs to no declared tier", str(raised.exception))

    def test_the_keel_may_not_import_a_language_package(self) -> None:
        code, said = self.gate({
            "__init__.py": '"""The keel."""\n',
            "errors.py": '"""A refusal."""\nimport slipwai_language_go\n',
        })
        self.assertEqual(code, 1)
        self.assertIn("the keel imports a language package: slipwai_language_go", said)

    def test_a_surface_naming_a_module_the_keel_has_not_got_is_refused(self) -> None:
        """An empty surface is held the same way: the file is checked whether or not a package exists."""
        code, said = self.gate({"__init__.py": '"""The keel."""\n'}, surface="slipwai.registry\n")
        self.assertEqual(code, 1)
        self.assertIn("lists slipwai.registry, which the keel does not have", said)

    def test_a_package_importing_off_the_surface_is_refused(self) -> None:
        code, said = self.gate(
            {"__init__.py": '"""The keel."""\n', "errors.py": '"""A refusal."""\n', "cli.py": '"""The edge."""\n'},
            surface="slipwai.errors\n",
            packages={"go/slipwai_language_go/backend.py": '"""Go."""\nfrom slipwai import errors, cli\n'},
        )
        self.assertEqual(code, 1)
        self.assertIn("language go imports slipwai.cli, which is not on the import surface", said)
        self.assertNotIn("slipwai.errors, which is not on the import surface", said)

    def test_a_package_directory_that_was_never_checked_out_is_reported(self) -> None:
        (self.root / "packages/go").mkdir(parents=True)
        code, said = self.gate({"__init__.py": '"""The keel."""\n'})
        self.assertEqual(code, 1)
        self.assertIn("git submodule update --init packages/go", said)

    def test_a_suite_over_the_budget_is_refused(self) -> None:
        body = "\n".join(f"x{n} = {n}" for n in range(structure.MODULE_BUDGET + 1))
        code, said = self.gate({"__init__.py": '"""The keel."""\n'}, suites={"test_big.py": body})
        self.assertEqual(code, 1)
        self.assertIn("over the", said)


class SurfaceTest(unittest.TestCase):
    def test_comments_and_blank_lines_are_not_modules(self) -> None:
        listing = "# a comment\n\nslipwai.registry\n  slipwai.loaded  # why\n"
        self.assertEqual(structure.import_surface(listing), {"slipwai.registry", "slipwai.loaded"})

    def test_the_surface_this_repository_ships_is_empty_and_still_read(self) -> None:
        """Phase 1 promises nothing. The file exists so the gate holds it from the first package onward."""
        self.assertTrue(structure.SURFACE.is_file())
        self.assertEqual(structure.import_surface(structure.SURFACE.read_text(encoding="utf-8")), set())


class RepositoryTest(unittest.TestCase):
    def test_this_repository_satisfies_its_own_gate(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = structure.main()
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("no upward imports and no cycles", out.getvalue())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
