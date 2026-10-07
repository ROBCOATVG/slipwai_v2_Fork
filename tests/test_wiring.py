"""The composition root's slice wiring, generated from the chart inside a region nobody edits.

The composition root was the second file every slice touched. Each added a line wiring its own use case,
all at the end of the same function, so two slices merging meant resolving the same three lines — the same
failure the events module had, with the same always-correct resolution of "take both".

What is held here: the lines come from the chart, they are in split order because wiring is the one place
order can matter, everything outside the markers is untouched, and a root edited inside them is refused.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.project import wiring

ROOT = "apps/service/src/ordering/main.py"
CHART: dict = {
    "slices": {
        "ORD-01": {"fairway": "ordering"},
        "ORD-02": {"fairway": "ordering"},
        "BIL-01": {"fairway": "billing"},
    }
}


def composition(region: str) -> str:
    return f'"""The process that listens."""\n\ndef build():\n    store = open_store()\n{region}\n    return app\n'


class NameTest(unittest.TestCase):
    def test_a_slice_id_becomes_an_identifier_every_language_takes(self) -> None:
        self.assertEqual(wiring.wiring_name("ORD-01"), "ord_01")

    def test_the_name_still_contains_the_slice_id_so_a_grep_finds_it(self) -> None:
        self.assertIn("ord", wiring.wiring_name("ORD-01"))


class RegionTest(unittest.TestCase):
    def test_one_line_per_slice_the_chart_names(self) -> None:
        block = wiring.region(ROOT, CHART)
        assert block is not None
        for name in ("ord_01", "ord_02", "bil_01"):
            with self.subTest(slice=name):
                self.assertIn(f"wire_{name}(", block)

    def test_the_order_is_the_chart_s_which_is_split_order(self) -> None:
        """Wiring is the one place two slices can depend on each other's having run."""
        block = wiring.region(ROOT, CHART)
        assert block is not None
        self.assertLess(block.index("ord_01"), block.index("ord_02"))
        self.assertLess(block.index("ord_02"), block.index("bil_01"))

    def test_a_fairway_may_take_only_its_own(self) -> None:
        block = wiring.region(ROOT, CHART, fairway="billing")
        assert block is not None
        self.assertIn("bil_01", block)
        self.assertNotIn("ord_01", block)

    def test_the_markers_say_not_to_edit_and_why(self) -> None:
        block = wiring.region(ROOT, CHART)
        assert block is not None
        self.assertIn("Never edit between the markers", block)
        self.assertIn("the next regeneration removes", block)

    def test_a_chart_with_no_slices_still_writes_a_region(self) -> None:
        """An empty region is a region; no region at all is a file the check cannot speak about."""
        block = wiring.region(ROOT, {"slices": {}})
        assert block is not None
        self.assertIn(wiring.BEGIN, block)
        self.assertIn("no slice wires anything yet", block)

    def test_a_language_this_does_not_write_for_gets_nothing(self) -> None:
        self.assertIsNone(wiring.region("cmd/main.rs", CHART))


class RewriteTest(unittest.TestCase):
    def test_everything_outside_the_markers_is_untouched(self) -> None:
        """A composition root also holds what a person wrote, and a generator taking the file over would
        be a generator owning a file it does not own."""
        before = composition(wiring.region(ROOT, {"slices": {}}) or "")
        after = wiring.rewritten(before, wiring.region(ROOT, CHART) or "")
        self.assertIn("store = open_store()", after)
        self.assertIn("return app", after)
        self.assertIn('"""The process that listens."""', after)

    def test_a_root_with_no_region_is_returned_unchanged(self) -> None:
        """Where the markers go is a decision about that file; guessing would put wiring before the store
        is open."""
        plain = "def build():\n    return app\n"
        self.assertEqual(wiring.rewritten(plain, wiring.region(ROOT, CHART) or ""), plain)

    def test_a_regeneration_is_what_two_slices_merging_produces(self) -> None:
        one = wiring.region(ROOT, {"slices": {"ORD-01": {}, "ORD-02": {}}})
        two = wiring.region(ROOT, {"slices": {"ORD-01": {}, "BIL-01": {}}})
        both = wiring.region(ROOT, CHART)
        assert one is not None and two is not None and both is not None
        for line in [*one.splitlines(), *two.splitlines()]:
            if "wire_" in line:
                with self.subTest(line=line.strip()):
                    self.assertIn(line, both)


class DriftTest(unittest.TestCase):
    def test_a_root_that_matches_the_chart_has_not_drifted(self) -> None:
        block = wiring.region(ROOT, CHART) or ""
        self.assertFalse(wiring.drifted(composition(block), block))

    def test_a_line_added_by_hand_inside_the_region_is_drift(self) -> None:
        """A line somebody added there is one the next regeneration silently removes."""
        block = wiring.region(ROOT, CHART) or ""
        edited = composition(block.replace(wiring.END, "    wire_by_hand(app, store)\n#" + " " + wiring.END))
        self.assertTrue(wiring.drifted(edited, block))

    def test_a_root_with_no_region_is_not_reported_as_drifted(self) -> None:
        self.assertFalse(wiring.drifted("def build():\n    return app\n", wiring.region(ROOT, CHART) or ""))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
