"""Where the product is, and how dark a merge is because of it.

In version 1 `release: flagged` was absolute. On a product in service that is right, because merging and
releasing are two decisions. On a product on the slipway, with no production and no actor but the team, it
is pure drag — a reader to call, two test paths, a key to hoist before every demo, and a park for a slice
with nothing holding it back. MANDA ran five berths under it on a product nobody used yet.

The fix held here is that the mode is not a knob. It follows from one fact about the product, because a
setting a person turns is wrong whenever somebody forgets to turn it, and a fact about where the product is
gets corrected because it is visibly untrue.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.project import release


def flat(text: str) -> str:
    return " ".join(text.split())


class ModeTest(unittest.TestCase):
    def test_a_slipway_product_merges_in_the_open(self) -> None:
        self.assertEqual(release.release_mode("slipway"), "open")

    def test_sea_trials_merges_by_omission(self) -> None:
        self.assertEqual(release.release_mode("sea-trials"), "keystone")

    def test_a_product_in_service_merges_behind_a_flag(self) -> None:
        self.assertEqual(release.release_mode("in-service"), "flagged")

    def test_a_product_with_no_state_recorded_is_treated_as_on_the_slipway(self) -> None:
        """The safe default is the one that generates least, not the one that generates most."""
        self.assertEqual(release.release_mode(""), "open")
        self.assertEqual(release.DEFAULT_STATE, "slipway")

    def test_promoted_is_kept_because_no_state_implies_it(self) -> None:
        """It is a fact about how a team deploys rather than about where the product is."""
        self.assertEqual(release.release_mode("slipway", declared="promoted"), "promoted")
        self.assertEqual(release.release_mode("in-service", declared="promoted"), "promoted")

    def test_any_other_declared_mode_loses_to_the_state(self) -> None:
        """A mode disagreeing with where the product is would be version 1's setting back again, wrong the
        moment somebody forgot to turn it."""
        self.assertEqual(release.release_mode("slipway", declared="flagged"), "open")

    def test_every_state_implies_a_mode_the_plan_names(self) -> None:
        for state in release.STATES:
            with self.subTest(state=state):
                self.assertIn(release.release_mode(state), release.MODES)


class FlagsTest(unittest.TestCase):
    def test_a_slipway_product_generates_no_flag_reader(self) -> None:
        """Which is most of what this buys: no reader, no second test path, no hoist before a demo."""
        self.assertFalse(release.flags_wanted("slipway"))

    def test_sea_trials_generates_no_flag_reader_either(self) -> None:
        """Keystone is dark by omission — the entry point is withheld, not gated."""
        self.assertFalse(release.flags_wanted("sea-trials"))

    def test_a_product_in_service_does(self) -> None:
        self.assertTrue(release.flags_wanted("in-service"))

    def test_a_promoted_product_does_not(self) -> None:
        self.assertFalse(release.flags_wanted("in-service", declared="promoted"))


class SectionTest(unittest.TestCase):
    def test_it_says_this_product_s_state_and_the_mode_that_follows(self) -> None:
        written = flat(release.release_section("slipway"))
        self.assertIn("state is **slipway**", written)
        self.assertIn("**open**", written)

    def test_it_is_read_once_at_the_merge_rather_than_weighed_per_slice(self) -> None:
        """Version 1 asked every slice and got the same answer every time, which is a stop that decides
        nothing and costs a stage."""
        written = flat(release.release_section("in-service"))
        self.assertIn("not a setting to weigh per slice", written)
        self.assertIn("a stop that costs a stage and decides nothing", written)

    def test_it_names_the_other_three_so_a_reader_knows_what_moving_would_change(self) -> None:
        written = flat(release.release_section("slipway"))
        for mode in ("keystone", "flagged", "promoted"):
            with self.subTest(mode=mode):
                self.assertIn(mode, written)

    def test_moving_the_product_is_a_person_s_and_an_adr(self) -> None:
        written = flat(release.release_section("slipway"))
        self.assertIn("a person's decision and an ADR", written)
        self.assertIn("A run never changes it", written)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
