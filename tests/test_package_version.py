"""Cutting a package's release: the entry assembled, the number written, the fragments gone.

The conformance suite holds a package's `VERSION`, `CHANGELOG.md` and `changelog.d/` together — a released
version must have an entry under its number and no fragments left over. Nothing gave a publisher a way to
satisfy that, so `VERSION` was a file to edit by hand, and editing it by hand is precisely what the suite
catches. Six packages were released that way this morning and every one of their first CI runs failed on it.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import package_new
from slipwai.errors import GenerationError
from slipwai.package_version import cut, released

CORE = "9.0"


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        package_new.write("extension", "lens", self.area, CORE)
        self.root = self.area / "lens"
        # The scaffold ships a first fragment so a new package can be released at once. These cases are
        # about the cut, so they start from an empty directory and write exactly what they mean to.
        for path in (self.root / "changelog.d").glob("*.md"):
            if path.name != "README.md":
                path.unlink()

    def fragment(self, name: str, level: str = "MINOR", body: str = "**It does a thing.**") -> None:
        (self.root / "changelog.d" / name).write_text(f"{level}\n\n{body}\n", encoding="utf-8")

    def changelog(self) -> str:
        return (self.root / "CHANGELOG.md").read_text(encoding="utf-8")

    def version(self) -> str:
        return (self.root / "VERSION").read_text(encoding="utf-8").strip()


class CutTest(Fixture):
    def test_the_entry_is_assembled_the_number_written_and_the_fragments_gone(self) -> None:
        self.fragment("one.md")
        version, _level, used = cut(self.root, "1.0.0")
        self.assertEqual((version, used), ("1.0.0", 1))
        self.assertIn("## 1.0.0", self.changelog())
        self.assertIn("It does a thing", self.changelog())
        self.assertEqual(self.version(), "1.0.0")
        self.assertEqual([p.name for p in (self.root / "changelog.d").iterdir()], ["README.md"])

    def test_the_first_release_carries_no_level(self) -> None:
        """It was bumped from nothing, and "MINOR relative to nothing" means nothing (D38). The
        conformance suite refuses a first entry that names one."""
        self.fragment("one.md")
        cut(self.root, "1.0.0")
        self.assertIn("## 1.0.0\n", self.changelog())
        self.assertNotIn("## 1.0.0 —", self.changelog())

    def test_a_later_release_does_carry_one(self) -> None:
        self.fragment("one.md")
        cut(self.root, "1.0.0")
        self.fragment("two.md", "PATCH")
        cut(self.root, "1.0.1")
        self.assertIn("## 1.0.1 — PATCH", self.changelog())

    def test_the_newest_entry_goes_above_the_released_ones(self) -> None:
        self.fragment("one.md")
        cut(self.root, "1.0.0")
        self.fragment("two.md", "PATCH")
        cut(self.root, "1.0.1")
        self.assertLess(self.changelog().index("## 1.0.1"), self.changelog().index("## 1.0.0"))

    def test_the_number_is_implied_by_what_the_fragments_claim(self) -> None:
        self.fragment("one.md")
        cut(self.root, "1.0.0")
        self.fragment("two.md", "MINOR")
        version, _level, _used = cut(self.root)
        self.assertEqual(version, "1.1.0")

    def test_the_level_is_the_highest_claimed(self) -> None:
        self.fragment("one.md")
        cut(self.root, "1.0.0")
        self.fragment("a.md", "PATCH")
        self.fragment("b.md", "MAJOR")
        version, level, _used = cut(self.root)
        self.assertEqual((version, level), ("2.0.0", "MAJOR"))


class RefusalTest(Fixture):
    def test_no_fragment_is_nothing_to_release_and_says_what_one_is(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            cut(self.root, "1.0.0")
        self.assertIn("nothing to release", str(refused.exception))
        self.assertIn("first line", str(refused.exception))

    def test_a_fragment_with_no_level_is_named(self) -> None:
        (self.root / "changelog.d/bad.md").write_text("no level here\n", encoding="utf-8")
        with self.assertRaises(GenerationError) as refused:
            cut(self.root, "1.0.0")
        self.assertIn("bad.md", str(refused.exception))

    def test_a_fragment_that_says_nothing_under_its_level_is_named(self) -> None:
        (self.root / "changelog.d/empty.md").write_text("MINOR\n\n", encoding="utf-8")
        with self.assertRaises(GenerationError) as refused:
            cut(self.root, "1.0.0")
        self.assertIn("empty.md", str(refused.exception))

    def test_a_version_already_released_is_refused(self) -> None:
        """A release is cut once. Cutting it twice writes a second entry for a number already out there."""
        self.fragment("one.md")
        cut(self.root, "1.0.0")
        self.fragment("two.md")
        with self.assertRaises(GenerationError) as refused:
            cut(self.root, "1.0.0")
        self.assertIn("cut once", str(refused.exception))

    def test_nothing_is_written_when_anything_is_wrong(self) -> None:
        """A cut that reached VERSION and then met a bad fragment would leave a number with no entry."""
        before = self.version()
        (self.root / "changelog.d/bad.md").write_text("no level\n", encoding="utf-8")
        with self.assertRaises(GenerationError):
            cut(self.root, "9.9.9")
        self.assertEqual(self.version(), before)
        self.assertNotIn("9.9.9", self.changelog())


class ReleasedTest(unittest.TestCase):
    def test_every_version_a_changelog_already_has_an_entry_for(self) -> None:
        said = "# Changelog\n\n## 2.0.0 — MAJOR\n\nbody\n\n## 1.0.0\n\nbody\n"
        self.assertEqual(released(said), ["2.0.0", "1.0.0"])

    def test_a_changelog_with_none(self) -> None:
        self.assertEqual(released("# Changelog\n\nnothing yet\n"), [])


class ScaffoldTest(Fixture):
    def test_the_makefile_offers_it(self) -> None:
        said = (self.root / "Makefile").read_text(encoding="utf-8")
        self.assertIn("slipwai package version .", said)

    def test_cutting_and_building_are_different_targets(self) -> None:
        """A CI job that rewrote the changelog would be rewriting the commit its tag points at."""
        said = (self.root / "Makefile").read_text(encoding="utf-8")
        self.assertIn("version:", said)
        self.assertIn("release:", said)


if __name__ == "__main__":
    unittest.main()


class ScaffoldReleasesTest(unittest.TestCase):
    """`new` writes a package that can be released without a hand edit, which is the whole chain:
    new → version → check → release → register."""

    def test_the_scaffold_ships_a_changelog_and_a_first_fragment(self) -> None:
        area = Path(tempfile.mkdtemp())
        package_new.write("extension", "lens", area, CORE)
        self.assertTrue((area / "lens/CHANGELOG.md").is_file())
        self.assertTrue((area / "lens/changelog.d/first-lens.md").is_file())

    def test_and_cutting_its_first_release_works_straight_away(self) -> None:
        area = Path(tempfile.mkdtemp())
        package_new.write("language", "rust", area, CORE)
        version, level, used = cut(area / "rust", "1.0.0")
        self.assertEqual((version, level, used), ("1.0.0", "", 1))
        self.assertIn("## 1.0.0", (area / "rust/CHANGELOG.md").read_text(encoding="utf-8"))
