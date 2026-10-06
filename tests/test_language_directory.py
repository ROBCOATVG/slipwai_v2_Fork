"""A language is a directory: where the keel looks, how a fragment is read, and how a package's Python is imported.

Every package here is a fake written by the test into a temporary directory, so what is proved is the loader and
nothing of any language. The refusals are the one line `language <name> (<directory>): <fault>`.
"""
from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path

import checkout_packages

from slipwai import language_directory
from slipwai.assets import ROOT, this_command
from slipwai.language_directory import VARIABLE, Package, Refused, directory, import_package, read

# The keel schema version the fakes are written against; `catalog.py` passes the real one.
CORE = "9.0"
FRAGMENT = {
    "name": "bad",
    "core": ">=9.0,<10",
    "order": 50,
    "family": "bad",
    "backends": {"bad": {"label": "Bad", "targets": ["none"], "options": {"http": ["none"]}}},
}
INIT = (
    "from slipwai.registry import Backend, Family, Language\n"
    "LANGUAGE = Language((Family('bad'),), (Backend('bad', 'bad'),))\n"
)


@contextlib.contextmanager
def environment(**changes: str | None) -> Iterator[None]:
    """Set or unset environment variables for the block, and put them back.

    `home=` moves the home directory on every platform: `Path.home()` reads `HOME` on POSIX and
    `USERPROFILE` on Windows, so a test that sets only `HOME` passes on a laptop and fails on the Windows
    leg, which is how this was found.
    """
    if "home" in changes:
        where = changes.pop("home")
        changes["HOME"] = changes["USERPROFILE"] = where
    before = {key: os.environ.get(key) for key in changes}
    for key, value in changes.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    try:
        yield
    finally:
        for key, value in before.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def write_package(parent: Path, name: str = "bad", fragment: dict | str | None = None, init: str | None = INIT) -> Path:
    """One package directory: `language.json`, and `slipwai_language_<name>/__init__.py` unless `init` is None."""
    root = parent / name
    root.mkdir(parents=True)
    if isinstance(fragment, str):
        body = fragment
    else:
        body = json.dumps({**FRAGMENT, "name": name} if fragment is None else fragment)
    (root / "language.json").write_text(body)
    # The flag reader `required_answers` gives a fake names a tree under the package's assets, and the loader holds
    # every source to being there, so the fake has the one it names.
    (root / "assets/languages/fake/flags").mkdir(parents=True)
    (root / "assets/languages/fake/flags/flags.x").write_text("x", encoding="utf-8")
    if init is not None:
        package = root / f"slipwai_language_{name.replace('-', '_')}"
        package.mkdir()
        (package / "__init__.py").write_text(init, encoding="utf-8")
    return root


def pin_beside(packages: Path) -> Path:
    """Link every package this checkout pins into `packages`, beside whatever a test wrote there, so the
    command line run against it has the first-party packages a generation needs.

    There are none to link until slice 3.8 pins them as submodules; the tests that need one skip rather
    than pass on nothing, so this is the directory a test wrote and no more.
    """
    packages.mkdir(parents=True, exist_ok=True)
    for root in sorted(checkout_packages.PACKAGES.glob("*/")) if checkout_packages.pinned() else []:
        if not (packages / root.name).exists():
            (packages / root.name).symlink_to(root)
    return packages


class DirectoryTest(unittest.TestCase):
    def test_the_variable_names_the_directory_and_replaces_the_default_whole(self) -> None:
        with environment(SLIPWAI_LANGUAGES="/tmp/l", home="/tmp/h"):
            self.assertEqual(directory(), Path("/tmp/l"))

    def test_without_the_variable_the_directory_is_under_home(self) -> None:
        with environment(SLIPWAI_LANGUAGES=None, home=str(Path("/tmp/h"))):
            self.assertEqual(directory(), Path("/tmp/h") / ".slipwai/languages")

    def test_a_directory_that_does_not_exist_holds_no_language_and_is_no_fault(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            self.assertEqual(read(Path(parent) / "absent", CORE), ([], []))

    def test_a_file_or_a_hidden_directory_is_not_a_language_and_is_skipped_silently(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            base = Path(parent)
            (base / "notes.txt").write_text("not a language", encoding="utf-8")
            (base / ".git").mkdir()
            (base / ".DS_Store").mkdir()
            write_package(base, "bad")
            packages, refusals = read(base, CORE)
            self.assertEqual([package.name for package in packages], ["bad"])
            self.assertEqual(refusals, [])


class FragmentTest(unittest.TestCase):
    """Phase 1: `language.json` alone, read before any package's Python exists."""

    def refused(self, **package: object) -> list[str]:
        with tempfile.TemporaryDirectory() as parent:
            root = write_package(Path(parent), **package)  # type: ignore[arg-type]
            packages, refusals = read(Path(parent), CORE)
            self.assertEqual(packages, [], "a refused package is not kept")
            return [line.replace(str(root), "<dir>") for line in refusals]

    def test_a_fragment_that_is_not_json_is_refused_with_the_parsers_words(self) -> None:
        self.assertEqual(
            self.refused(fragment="{"),
            ["language bad (<dir>): language.json is not valid JSON: "
             "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"],
        )

    def test_a_fragment_lacking_a_key_names_it(self) -> None:
        for key in ("core", "name", "order", "family", "backends"):
            fragment = {k: v for k, v in {**FRAGMENT, "name": "bad"}.items() if k != key}
            self.assertEqual(self.refused(fragment=fragment), [f"language bad (<dir>): language.json lacks {key}"], key)

    def test_a_fragment_naming_another_directory_is_refused(self) -> None:
        self.assertEqual(
            self.refused(name="go", fragment={**FRAGMENT, "name": "golang"}),
            ["language go (<dir>): language.json names golang, and its directory is go"],
        )

    def test_a_key_of_the_wrong_kind_is_refused(self) -> None:
        for key, value in (("order", "30"), ("backends", {}), ("core", 9), ("family", None)):
            (line,) = self.refused(fragment={**FRAGMENT, key: value})
            self.assertTrue(line.startswith("language bad (<dir>): language.json's "), line)
            self.assertIn(key, line)

    def test_a_key_core_does_not_know_is_ignored(self) -> None:
        # `requires` was the second example until S10 made it a key the keel reads (`test_framework_packages`).
        extra = {**FRAGMENT, "homepage": "https://example.test", "licence": {"spdx": "MIT"}}
        with tempfile.TemporaryDirectory() as parent:
            write_package(Path(parent), fragment=extra)
            packages, refusals = read(Path(parent), CORE)
            self.assertEqual(refusals, [])
            self.assertEqual(packages[0].fragment["homepage"], "https://example.test")

    def test_a_range_that_does_not_parse_is_refused_in_the_fragments_words(self) -> None:
        self.assertEqual(
            self.refused(fragment={**FRAGMENT, "core": ">9.0"}),
            ["language bad (<dir>): core range '>9.0' is not >=, < or == over dotted integers"],
        )

    def test_a_core_older_than_the_range_is_told_to_upgrade(self) -> None:
        self.assertEqual(
            self.refused(fragment={**FRAGMENT, "core": ">=9.1,<10"}),
            ["language bad (<dir>): needs core schema >=9.1,<10, and this core speaks 9.0: "
             f"{this_command()} upgrade"],
        )

    def test_a_core_newer_than_the_range_is_told_to_get_a_newer_package(self) -> None:
        self.assertEqual(
            self.refused(fragment={**FRAGMENT, "core": ">=8,<9"}),
            ["language bad (<dir>): needs core schema >=8,<9, and this core speaks 9.0: "
             "it needs a version of bad built for schema 9"],
        )

    def test_one_refused_package_does_not_stop_the_next(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            write_package(Path(parent), "bad", fragment="{")
            write_package(Path(parent), "good", init=None)
            packages, refusals = read(Path(parent), CORE)
            self.assertEqual([package.name for package in packages], ["good"])
            self.assertEqual(len(refusals), 1)


class ImportTest(unittest.TestCase):
    """Phase 2: the package's Python, imported from its own directory."""

    def load(self, **package: object) -> tuple[Path, Package]:
        parent = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(parent, ignore_errors=True))
        root = write_package(parent, **package)  # type: ignore[arg-type]
        packages, refusals = read(parent, CORE)
        self.assertEqual(refusals, [])
        return root, packages[0]

    def refusal(self, **package: object) -> str:
        root, loaded = self.load(**package)
        with self.assertRaises(Refused) as caught:
            import_package(loaded)
        return str(caught.exception).replace(str(root), "<dir>")

    def tearDown(self) -> None:
        for name in [name for name in sys.modules if name.startswith("slipwai_language_bad")]:
            del sys.modules[name]

    def test_a_package_is_imported_from_its_own_directory_and_the_path_is_untouched(self) -> None:
        root, loaded = self.load()
        path = list(sys.path)
        language = import_package(loaded)
        self.assertEqual(sys.path, path)
        self.assertEqual([backend.key for backend in language.backends], ["bad"])
        module_file = sys.modules["slipwai_language_bad"].__file__
        assert module_file is not None
        self.assertTrue(Path(module_file).resolve().is_relative_to(root.resolve()))

    def test_a_package_with_no_python_package_is_refused(self) -> None:
        self.assertEqual(
            self.refusal(init=None),
            "language bad (<dir>): has no Python package slipwai_language_bad",
        )

    def test_an_exception_at_import_is_one_line_and_leaves_nothing_behind(self) -> None:
        line = self.refusal(init="import slipwai\n1 / 0\n")
        self.assertEqual(
            line, "language bad (<dir>): slipwai_language_bad failed to import: ZeroDivisionError: division by zero"
        )
        self.assertNotIn("slipwai_language_bad", sys.modules)

    def test_a_submodule_imported_before_the_failure_is_removed_with_it(self) -> None:
        parent = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(parent, ignore_errors=True))
        root = write_package(parent, init="from . import helper\n1 / 0\n")
        (root / "slipwai_language_bad" / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
        packages, _ = read(parent, CORE)
        with self.assertRaises(Refused):
            import_package(packages[0])
        self.assertEqual([name for name in sys.modules if name.startswith("slipwai_language_bad")], [])

    def test_a_package_without_language_or_with_the_wrong_kind_is_refused(self) -> None:
        self.assertEqual(
            self.refusal(init="X = 1\n"), "language bad (<dir>): slipwai_language_bad has no LANGUAGE"
        )
        self.assertEqual(
            self.refusal(init="LANGUAGE = {}\n"),
            "language bad (<dir>): slipwai_language_bad's LANGUAGE is a dict, not a Language",
        )

    def test_backends_that_differ_from_the_fragments_are_refused(self) -> None:
        init = INIT.replace("Backend('bad', 'bad')", "Backend('bad2', 'bad')")
        self.assertEqual(
            self.refusal(init=init),
            "language bad (<dir>): language.json declares bad and its LANGUAGE declares bad2",
        )

    def test_the_module_is_named_with_a_dash_read_as_an_underscore(self) -> None:
        self.assertEqual(language_directory.module_name("go-gin"), "slipwai_language_go_gin")


TESTS = Path(__file__).resolve().parent
GOOD = (
    "from registry_fakes import fake_language\n"
    "LANGUAGE = fake_language('bad', 'bad')\n"
)
FAULTS: dict[str, dict[str, object]] = {
    "3a not json": {"fragment": "{"},
    "3b lacks core": {"fragment": {k: v for k, v in FRAGMENT.items() if k != "core"}},
    "3c other name": {"fragment": {**FRAGMENT, "name": "golang"}},
    "3d no python": {"init": None},
    "3e raises": {"init": "1 / 0\n"},
    "3f no language": {"init": "X = 1\n"},
    "3g other backend": {"init": GOOD.replace("'bad', 'bad'", "'bad2', 'bad'")},
    "3h protocol": {"init": GOOD.replace("fake_language(", "no_ready(").replace(
        "from registry_fakes import fake_language\n",
        "from registry_fakes import fake_language, required_answers\nfrom slipwai.registry import READY_PATH\n"
        "def no_ready(k, f):\n    return fake_language(k, f, required_answers(without=(READY_PATH,)))\n")},
}


@unittest.skipUnless(all(checkout_packages.installed(n) for n in ("go",)),
                     "needs the first-party packages, which the keel never installs")
class EndToEndTest(unittest.TestCase):
    """The same refusals through the command line: one line on stderr, the verb runs, everything else loads."""

    def run_slipwai(self, languages: Path, *arguments: str, output: Path) -> subprocess.CompletedProcess[str]:
        environment = {**os.environ, VARIABLE: str(pin_beside(languages)), "PYTHONPATH": str(TESTS)}
        environment.pop("CRUISE_RUNNER", None)
        environment.pop("CRUISE_ITERATION", None)
        return subprocess.run(
            [str(ROOT / "slipwai"), *arguments, "--output", str(output)],
            capture_output=True, text=True, env=environment, check=False,
        )

    def test_a_refused_language_is_one_line_on_stderr_and_the_verb_still_runs(self) -> None:
        for label, package in FAULTS.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as parent:
                languages, output = Path(parent) / "languages", Path(parent) / "out"
                write_package(languages, **package)  # type: ignore[arg-type]
                done = self.run_slipwai(languages, "generate", "demo", "--backend", "typescript", "--frontend", "none",
                                        output=output)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertTrue((output / "demo").is_dir())
                refusals = [line for line in done.stderr.splitlines() if line.startswith("slipwai: language bad")]
                self.assertEqual(len(refusals), 1, done.stderr)
                self.assertNotIn("Traceback", done.stderr)

    def test_a_backend_a_refused_package_declared_is_named_as_installed_and_refused(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            languages, output = Path(parent) / "languages", Path(parent) / "out"
            write_package(languages, **FAULTS["3e raises"])  # type: ignore[arg-type]
            done = self.run_slipwai(languages, "generate", "demo", "--backend", "bad", output=output)
            self.assertEqual(done.returncode, 2)
            self.assertIn("--backend bad is installed and the loader refused it — language bad (", done.stderr)


if __name__ == "__main__":
    unittest.main()
