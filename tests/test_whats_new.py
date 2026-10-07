"""What `slipwai upgrade` says you got, and the one upgrade that is told as a crossing.

An upgrade that says `Successfully installed slipwai-2.1.0` has told you a number. Finding out what the
number means is a web page, which means most people never do — so the next time something behaves
differently they look for a bug rather than for a change.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.whats_new import SHOWN, between, crossed_major, crossing_into_two, entries, lines, read

CHANGELOG = """# Changelog

Preamble that is not an entry.

## 2.1.0 — MINOR

**Extensions install from a git URL.** And a sentence about it.

**Catch-up:** nothing.

## 2.0.1 — PATCH

**A fix.**

## 2.0.0 — MAJOR

**Version 2.**
"""


class ParseTest(unittest.TestCase):
    def test_every_entry_is_read_newest_first_with_its_level(self) -> None:
        found = entries(CHANGELOG)
        self.assertEqual([one[0] for one in found], ["2.1.0", "2.0.1", "2.0.0"])
        self.assertEqual(found[0][1], "MINOR")

    def test_the_preamble_is_not_an_entry(self) -> None:
        self.assertNotIn("Preamble", "".join(body for _, _, body in entries(CHANGELOG)))

    def test_an_entry_with_no_level_is_still_an_entry(self) -> None:
        self.assertEqual(entries("## 1.0.0\n\nThe first one.\n")[0][0], "1.0.0")

    def test_a_changelog_that_is_not_there_is_no_entries_and_not_a_fault(self) -> None:
        self.assertEqual(read(Path(tempfile.mkdtemp()) / "nothing.md"), [])


class BetweenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.found = entries(CHANGELOG)

    def test_only_the_entries_actually_crossed(self) -> None:
        crossed = between(self.found, "2.0.0", "2.1.0")
        self.assertEqual([one[0] for one in crossed], ["2.1.0", "2.0.1"])

    def test_the_version_you_had_is_not_one_you_crossed(self) -> None:
        self.assertNotIn("2.0.0", [one[0] for one in between(self.found, "2.0.0", "2.1.0")])

    def test_the_version_you_got_is(self) -> None:
        self.assertIn("2.1.0", [one[0] for one in between(self.found, "2.0.1", "2.1.0")])


class SaidTest(unittest.TestCase):
    def setUp(self) -> None:
        self.found = entries(CHANGELOG)

    def test_what_changed_is_printed_rather_than_linked_to(self) -> None:
        said = "\n".join(lines("2.0.1", "2.1.0", self.found))
        self.assertIn("2.0.1 → 2.1.0", said)
        self.assertIn("Extensions install from a git URL", said)

    def test_a_long_absence_is_counted_rather_than_scrolled_past(self) -> None:
        many = [(f"1.{n}.0", "MINOR", f"Change {n}.") for n in range(20, 0, -1)]
        said = "\n".join(lines("1.0.0", "1.20.0", many))
        self.assertIn("more release(s)", said)
        self.assertEqual(said.count("— MINOR"), SHOWN)

    def test_a_version_the_changelog_says_nothing_about_says_that(self) -> None:
        """Printing nothing would leave "did it work?" as the question."""
        said = "\n".join(lines("2.1.0", "3.0.0", []))
        self.assertIn("not in this copy", said)

    def test_the_same_version_twice_is_not_a_list_of_everything(self) -> None:
        said = "\n".join(lines("2.1.0", "2.1.0", self.found))
        self.assertIn("not in this copy", said)


class CrossingTest(unittest.TestCase):
    def test_a_major_is_a_crossing_and_a_minor_is_not(self) -> None:
        self.assertTrue(crossed_major("1.5.2", "2.0.0"))
        self.assertFalse(crossed_major("2.0.0", "2.1.0"))
        self.assertFalse(crossed_major("2.1.0", "2.0.0"))

    def test_only_the_one_to_two_crossing_gets_the_banner(self) -> None:
        """The banner says what version 2 *is*, which somebody wrote once; arithmetic cannot produce it."""
        self.assertTrue(crossing_into_two("1.5.2", "2.0.0"))
        self.assertFalse(crossing_into_two("2.1.0", "3.0.0"))

    def test_another_major_is_still_told_as_one_without_pretending_to_know_it(self) -> None:
        said = "\n".join(lines("2.1.0", "3.0.0", []))
        self.assertIn("crosses a major version", said)
        self.assertNotIn("slipwai 2 —", said)

    def test_the_crossing_says_what_version_2_is_rather_than_listing_releases(self) -> None:
        """Eleven paragraphs of changelog about a different factory is a day of confusion."""
        said = "\n".join(lines("1.5.2", "2.0.0", entries(CHANGELOG)))
        self.assertIn("a different factory", said)
        for thing in ("Languages are packages", "The loop has captains", "The state is in the log"):
            self.assertIn(thing, said)

    def test_it_names_the_one_command_that_moves_a_project(self) -> None:
        said = "\n".join(lines("1.5.2", "2.0.0", entries(CHANGELOG)))
        self.assertIn("slipwai migrate", said)

    def test_and_says_nothing_is_migrated_behind_your_back(self) -> None:
        self.assertIn("behind your back", "\n".join(lines("1.5.2", "2.0.0", [])))

    def test_it_says_where_you_were_and_where_you_are(self) -> None:
        said = "\n".join(lines("1.5.2", "2.0.0", []))
        self.assertIn("You were on 1.5.2. You are on 2.0.0.", said)


if __name__ == "__main__":
    unittest.main()
