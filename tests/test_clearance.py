"""Clearance: what lets a slice start, and what it says when it may not.

Version 1 asked whether a slice's own contract was settled, which a slice could only answer about itself.
That serialised a fresh fairway, because nothing said what a slice was waiting *for*. The rule here is the
one issue #32 asked for: a slice starts when every mark it steers by has been set, and a mark is set when
some slice wrote a `mark-set` line for it at its own first stage. So a sibling unblocks this one by having
planned, not by having merged, which is the whole of the parallelism the plan promises.

Two things are held here besides the rule. State comes from log lines and never from a status field,
because in the first attempt `model.yaml` said `planned` for eight slices that were built and merged. And a
refusal names every mark that is missing and who owes it, because a fairway told one blocker at a time is a
fairway blocked once per blocker.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.project import chart

CHART: dict = {
    "v": 1,
    "feature": "ordering",
    "fairways": {"ordering": {}, "billing": {}},
    "marks": {"OrderPlaced": {}, "InvoiceRaised": {}, "PricingPort": {}},
    "slices": {
        "ORD-01": {"fairway": "ordering", "capability": "place-an-order",
                   "sets": ["OrderPlaced"], "steers_by": []},
        "ORD-02": {"fairway": "ordering", "capability": "place-an-order",
                   "sets": ["PricingPort"], "steers_by": []},
        "BIL-01": {"fairway": "billing", "capability": "bill-an-order",
                   "sets": ["InvoiceRaised"], "steers_by": ["OrderPlaced", "PricingPort"]},
    },
}


def mark_set(mark: str, by: str) -> dict:
    return {"v": 1, "kind": "mark-set", "mark": mark, "slice": by, "fairway": "ordering"}


class ClearanceTest(unittest.TestCase):
    def test_a_slice_steering_by_nothing_starts_at_once(self) -> None:
        """Which is what lets a fresh fairway fan out on its first iteration."""
        self.assertIs(chart.cleared(CHART, [], "ORD-01"), True)

    def test_a_slice_is_cleared_when_every_mark_it_steers_by_is_set(self) -> None:
        lines = [mark_set("OrderPlaced", "ORD-01"), mark_set("PricingPort", "ORD-02")]
        self.assertIs(chart.cleared(CHART, lines, "BIL-01"), True)

    def test_one_mark_short_is_not_cleared(self) -> None:
        self.assertIsInstance(chart.cleared(CHART, [mark_set("OrderPlaced", "ORD-01")], "BIL-01"), str)

    def test_the_refusal_names_every_missing_mark_and_who_owes_it(self) -> None:
        """A fairway told one blocker at a time is a fairway blocked once per blocker."""
        why = chart.cleared(CHART, [], "BIL-01")
        assert isinstance(why, str)
        self.assertIn("OrderPlaced (set by ORD-01)", why)
        self.assertIn("PricingPort (set by ORD-02)", why)

    def test_a_mark_nobody_sets_says_the_chart_is_wrong_rather_than_blaming_a_slice(self) -> None:
        broken: dict = {**CHART, "slices": {"BIL-01": {"steers_by": ["ShipmentBooked"], "sets": []}}}
        why = chart.cleared(broken, [], "BIL-01")
        assert isinstance(why, str)
        self.assertIn("no slice sets it", why)

    def test_a_slice_the_chart_does_not_name_is_refused_and_not_cleared(self) -> None:
        """Answering True for a slice nobody charted would clear anything anyone asked about."""
        why = chart.cleared(CHART, [], "SHP-01")
        assert isinstance(why, str)
        self.assertIn("not on the chart", why)

    def test_a_merge_is_not_what_clears_a_sibling(self) -> None:
        """A `mark-set` line is written at the setter's first stage, in its own worktree, long before it
        merges. If a merge were the signal, every fairway would wait on every other one."""
        lines = [mark_set("OrderPlaced", "ORD-01"), mark_set("PricingPort", "ORD-02"),
                 {"kind": "claimed", "slice": "ORD-01"}]
        self.assertIs(chart.cleared(CHART, lines, "BIL-01"), True)
        self.assertNotIn("merged", [line.get("kind") for line in lines])

    def test_a_line_kind_this_reader_does_not_know_is_ignored(self) -> None:
        """The deck log holds eleven kinds and grows. A reader that refused the unfamiliar would break
        every time one was added."""
        lines = [{"kind": "heartbeat"}, {"kind": "tokens", "mark": "OrderPlaced"},
                 mark_set("OrderPlaced", "ORD-01"), mark_set("PricingPort", "ORD-02")]
        self.assertIs(chart.cleared(CHART, lines, "BIL-01"), True)

    def test_a_mark_set_line_with_no_mark_sets_nothing(self) -> None:
        self.assertEqual(chart.marks_set([{"kind": "mark-set", "slice": "ORD-01"}]), set())


class ReadySetTest(unittest.TestCase):
    def test_the_cleared_set_is_in_the_charts_own_order_which_is_split_order(self) -> None:
        self.assertEqual(chart.cleared_slices(CHART, []), ["ORD-01", "ORD-02"])

    def test_a_setter_planning_clears_what_waits_on_it(self) -> None:
        lines = [mark_set("OrderPlaced", "ORD-01"), mark_set("PricingPort", "ORD-02")]
        self.assertEqual(chart.cleared_slices(CHART, lines), ["ORD-01", "ORD-02", "BIL-01"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
