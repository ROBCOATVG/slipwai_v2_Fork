"""The registry this process actually runs on: built once, from the catalogue and the package directory.

`registry.registry()` is the entry point every other module asks, and `loaded.build` is what answers it.
The two halves of the keel meet here — the catalogue says which backends there should be, the directory
says which packages are installed — and the whole point of the module is that a package which does not
load is a line, not a crash, and the keel carries on with the ones that do.

With nothing installed the registry is empty, and that is a working keel with a short menu rather than a
broken one. The cases with a real package in the directory arrive with the submodules in slice 3.8; what
is held here is everything that is true with none, which includes every refusal path that does not need
a package on disk to provoke.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.catalog import CATALOG, PACKAGES
from slipwai.loaded import build, refusals, sound, without_later
from slipwai.registry import Registry, registry


class EmptyKeelTest(unittest.TestCase):
    def test_the_process_registry_builds_from_the_package_in_the_directory(self) -> None:
        """One package in, one backend out. The keel itself still answers for none."""
        built = registry()
        self.assertIsInstance(built, Registry)
        self.assertEqual(set(built.backends), {"toy-plain"})
        self.assertEqual(set(built.families), {"toy"})

    def test_a_registry_of_no_package_answers_nothing_and_that_is_not_a_failure(self) -> None:
        built, refused = build((), [], CATALOG)
        self.assertEqual((dict(built.backends), refused), ({}, []))

    def test_it_is_built_once_per_process(self) -> None:
        """`registry()` is cached: the loader imports a package's Python, and importing it twice would run
        somebody else's module twice."""
        self.assertIs(registry(), registry())

    def test_nothing_is_refused_when_there_is_nothing_to_refuse(self) -> None:
        self.assertEqual(refusals(), [])

    def test_the_keels_own_catalogue_is_sound_before_any_package_is_folded_in(self) -> None:
        """If this is false the fault is the keel's, and no package may be blamed for it. Asked of the
        catalogue with the installed packages taken back out, which is what `sound` is for."""
        self.assertTrue(sound((), list(PACKAGES), CATALOG))

    def test_build_takes_no_language_of_its_own(self) -> None:
        """Version 1 passed the built-in languages first. Version 2 has none — every language is a package
        — and `build(())` is what the process asks for."""
        built, refused = build((), [], CATALOG)
        self.assertEqual((dict(built.backends), refused), ({}, []))


class WithoutLaterTest(unittest.TestCase):
    """A package is checked against the catalogue as it stands *before* the packages after it are folded
    in, so a fault is attributed to the package that caused it rather than to whichever came last."""

    def test_a_catalogue_with_nothing_later_to_remove_is_unchanged(self) -> None:
        self.assertEqual(without_later(CATALOG, []), CATALOG)

    def test_the_catalogue_it_is_given_is_not_the_one_it_changes(self) -> None:
        """The process's own `CATALOG` is read by everything; a check that edited it would poison them all."""
        before = CATALOG["backends"].copy()
        without_later(CATALOG, [])
        self.assertEqual(CATALOG["backends"], before)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
