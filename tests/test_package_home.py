"""Where this machine keeps what it has installed, and the move from the name it used to have.

`~/.slipwai/languages` held extensions as well as languages, which is a name that costs an hour the first
time somebody goes looking for `codegraph` in it. The rename was decided 2026-10-06 and written into the
plan; slice 8.3 carries it into the keel, because a directory cannot move without moving the packages
already in it.

Every test here writes into a temporary home, so the suite never touches the one a person has installed
into.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from test_language_directory import CORE, environment, write_package

from slipwai.language_directory import directory, read


class MovedTest(unittest.TestCase):
    def test_an_install_made_under_the_old_name_is_found_moved_and_loaded_from_the_new_one(self) -> None:
        """Slice 8.3's own line. The directory holds extensions as well as languages, so `languages/` was
        a name that would cost an hour the first time somebody went looking for `codegraph` in it."""
        with tempfile.TemporaryDirectory() as parent:
            home = Path(parent)
            write_package(home / ".slipwai/languages")
            with environment(SLIPWAI_LANGUAGES=None, home=str(home)):
                where = directory()
            self.assertEqual(where, home / ".slipwai/packages")
            self.assertFalse((home / ".slipwai/languages").exists(), "the old directory is still there")
            self.assertEqual([package.name for package, in [(p,) for p in read(where, CORE)[0]]], ["bad"])

    def test_both_directories_is_somebody_being_deliberate_and_neither_is_touched(self) -> None:
        """Two is a state a keel cannot resolve: merging them would be guessing which copy was meant."""
        with tempfile.TemporaryDirectory() as parent:
            home = Path(parent)
            write_package(home / ".slipwai/languages", "old")
            write_package(home / ".slipwai/packages", "new")
            with environment(SLIPWAI_LANGUAGES=None, home=str(home)):
                self.assertEqual(directory(), home / ".slipwai/packages")
            self.assertTrue((home / ".slipwai/languages/old").is_dir(), "the old directory was taken away")

    def test_nothing_installed_anywhere_is_the_new_name_and_no_move(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            with environment(SLIPWAI_LANGUAGES=None, home=parent):
                self.assertEqual(directory(), Path(parent) / ".slipwai/packages")
            self.assertFalse((Path(parent) / ".slipwai/packages").exists(), "asking where wrote a directory")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
