"""The capability: what a person's demo is of, and what says one is owed.

Version 1 stopped a person at the end of every slice and showed them a fraction of a capability to assemble
in their head. The hand still walks a slice's examples and records a verdict — a test that passes and a path
that works are different claims, and only one of them is machine-checked — and nobody is stopped for it. The
stop a person attends runs when a capability's last slice has merged.

The other thing held here is that acceptance and hoisting never touch. Acceptance says the capability is
right; hoisting says the business wants it live, which may be another quarter or never. A capability the
business is deliberately holding back is not a late one, and a board that derived one state from the other
could not tell the two apart.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.project import demo_stop

ROOT = Path(__file__).resolve().parents[1]


def module():
    path = ROOT / "assets/toolkit/scripts/agents/capabilities.py"
    spec = importlib.util.spec_from_file_location("capabilities_script", path)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(loaded)
    return loaded


CAPS = module()

CHART: dict = {
    "slices": {
        "ORD-01": {"capability": "place-an-order", "fairway": "ordering"},
        "ORD-02": {"capability": "place-an-order", "fairway": "ordering"},
        "BIL-01": {"capability": "bill-an-order", "fairway": "billing"},
    }
}


def merged(slice_id: str) -> dict:
    return {"v": 1, "kind": "merged", "slice": slice_id, "fairway": "ordering", "commit": "abc"}


def accepted(capability: str) -> dict:
    return {"v": 1, "kind": "accepted", "capability": capability, "fairway": "ordering"}


class GroupingTest(unittest.TestCase):
    def test_a_capability_is_its_slices_in_split_order(self) -> None:
        self.assertEqual(CAPS.slices_by_capability(CHART)["place-an-order"], ["ORD-01", "ORD-02"])

    def test_a_slice_with_no_capability_is_in_none(self) -> None:
        """check-chart refuses that chart; this reader does not invent a group for it."""
        self.assertEqual(CAPS.slices_by_capability({"slices": {"X": {"fairway": "ordering"}}}), {})


class DueTest(unittest.TestCase):
    def test_nothing_is_due_before_the_last_slice_merges(self) -> None:
        rows = CAPS.state(CHART, [merged("ORD-01")])
        self.assertEqual(CAPS.due(rows), [])

    def test_a_capability_is_due_when_its_last_slice_merges(self) -> None:
        rows = CAPS.state(CHART, [merged("ORD-01"), merged("ORD-02")])
        self.assertEqual([row["capability"] for row in CAPS.due(rows)], ["place-an-order"])

    def test_a_part_merged_capability_says_what_it_waits_on(self) -> None:
        rows = CAPS.state(CHART, [merged("ORD-01")])
        row = next(r for r in rows if r["capability"] == "place-an-order")
        self.assertEqual(row["waiting"], ["ORD-02"])
        self.assertEqual(row["merged"], 1)

    def test_an_accepted_capability_is_no_longer_due(self) -> None:
        rows = CAPS.state(CHART, [merged("ORD-01"), merged("ORD-02"), accepted("place-an-order")])
        self.assertEqual(CAPS.due(rows), [])

    def test_one_capability_completing_does_not_make_another_due(self) -> None:
        rows = CAPS.state(CHART, [merged("ORD-01"), merged("ORD-02")])
        self.assertNotIn("bill-an-order", [row["capability"] for row in CAPS.due(rows)])


class ReleaseTest(unittest.TestCase):
    def test_accepted_and_hoisted_are_separate_and_neither_is_derived(self) -> None:
        """A capability the business is deliberately holding back is not a late one."""
        rows = CAPS.state(CHART, [merged("ORD-01"), merged("ORD-02"), accepted("place-an-order")])
        row = next(r for r in rows if r["capability"] == "place-an-order")
        self.assertTrue(row["accepted"])
        self.assertFalse(row["hoisted"], "acceptance must never imply a hoist")

    def test_a_capability_can_be_hoisted_and_the_two_states_stay_apart(self) -> None:
        rows = CAPS.state(CHART, [merged("ORD-01"), merged("ORD-02"), accepted("place-an-order"),
                                  {"v": 1, "kind": "flag-hoisted", "flag": "place-an-order", "where": "prod"}])
        row = next(r for r in rows if r["capability"] == "place-an-order")
        self.assertTrue(row["accepted"])
        self.assertTrue(row["hoisted"])

    def test_the_trigger_mentions_no_flag_at_all(self) -> None:
        """Under the open release mode there is no flag, and the demo still happens."""
        rows = CAPS.state(CHART, [merged("BIL-01")])
        self.assertEqual([row["capability"] for row in CAPS.due(rows)], ["bill-an-order"])


class DemoStopTest(unittest.TestCase):
    def section(self) -> str:
        return " ".join(demo_stop.demo_stop(event=True).split())

    def test_the_stop_says_it_is_per_capability(self) -> None:
        self.assertIn("per capability, not per slice", self.section())

    def test_the_per_slice_walk_stops_nobody(self) -> None:
        section = self.section()
        self.assertIn("records a verdict in three words", section)
        self.assertIn("nobody is stopped for that", section.lower())

    def test_it_names_the_command_that_says_what_is_owed(self) -> None:
        self.assertIn("capabilities.py --due", self.section())

    def test_accepting_is_not_a_release_decision(self) -> None:
        section = self.section()
        self.assertIn("Accepting it is not a release decision", section)
        self.assertIn("nothing here asks about a flag or moves one", section)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
