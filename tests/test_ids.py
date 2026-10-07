"""Ids that carry their fairway, counted out of the log that recorded the thing being counted.

In the first attempt every berth took the next number after the last one it could see in its own checkout,
and every berth appended to one `decisions.md`. That cost 54 renumbering commits in a single night, and one
renumber rewrote 91 citations — every one of which had been correct when it was written. A claimed range of
numbers only shrinks the window; it does not close it.

So the counter is per fairway and the id says which. Two fairways cannot collide because they are not
counting the same thing, and nothing is renumbered, so a citation written today still resolves in a year.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


def ids_module(tree: Path):
    """The script as a generated project runs it: by path, rooted on that project."""
    spec = importlib.util.spec_from_file_location(f"ids_{tree.name}", tree / "scripts/agents/ids.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


class IdTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts/agents").mkdir(parents=True)
        shutil.copy(ROOT / "assets/toolkit/scripts/agents/ids.py", self.tree / "scripts/agents/ids.py")
        (self.tree / "project.json").write_text("{}", encoding="utf-8")
        (self.tree / ".slipwai/logs/ordering").mkdir(parents=True)
        self.ids = ids_module(self.tree)

    def write(self, fairway: str, lines: list[dict]) -> None:
        path = self.tree / f".slipwai/logs/ordering/{fairway}.jsonl"
        path.write_text("".join(json.dumps({"v": 1, **line}) + "\n" for line in lines), encoding="utf-8")

    def decision(self, fairway: str) -> dict:
        return {"kind": "decision", "fairway": fairway, "id": "x", "what": "something"}

    def test_the_first_id_of_a_fairway_is_one(self) -> None:
        self.assertEqual(self.ids.next_id("decision", "ORD", "ordering"), "D-ORD-01")

    def test_the_id_carries_its_fairway(self) -> None:
        self.write("ORD", [self.decision("ORD")] * 6)
        self.assertEqual(self.ids.next_id("decision", "ORD", "ordering"), "D-ORD-07")

    def test_two_fairways_deciding_at_once_cannot_mint_the_same_id(self) -> None:
        """The failure that cost 54 renumbering commits in one night."""
        self.write("ORD", [self.decision("ORD")] * 6)
        self.write("BIL", [self.decision("BIL")] * 2)
        self.assertEqual(self.ids.next_id("decision", "ORD", "ordering"), "D-ORD-07")
        self.assertEqual(self.ids.next_id("decision", "BIL", "ordering"), "D-BIL-03")

    def test_the_count_comes_from_the_log_and_not_from_a_file(self) -> None:
        """A rendered file can be stale, mid-merge, or an aggregate of two fairways. The log cannot."""
        self.write("ORD", [self.decision("ORD")] * 3)
        (self.tree / "fairways").mkdir()
        self.assertEqual(self.ids.next_id("decision", "ORD", "ordering"), "D-ORD-04")

    def test_only_the_kind_being_counted_is_counted(self) -> None:
        self.write("ORD", [self.decision("ORD"), {"kind": "heartbeat", "fairway": "ORD"},
                           {"kind": "claimed", "fairway": "ORD", "slice": "ORD-01"}])
        self.assertEqual(self.ids.next_id("decision", "ORD", "ordering"), "D-ORD-02")

    def test_an_adversary_finding_has_its_own_counter(self) -> None:
        self.write("BIL", [{"kind": "stowed", "fairway": "BIL", "slice": "BIL-01",
                            "from": "adversary", "what": "wording"}] * 2)
        self.assertEqual(self.ids.next_id("adversary", "BIL", "ordering"), "A-BIL-03")

    def test_a_kind_with_no_scheme_is_refused_rather_than_given_a_guessed_prefix(self) -> None:
        """An id is a citation, and a wrong one resolves to nothing."""
        with self.assertRaises(SystemExit) as refused:
            self.ids.next_id("vibes", "ORD", "ordering")
        self.assertIn("no id scheme", str(refused.exception))

    def test_a_log_line_nobody_can_read_stops_the_count(self) -> None:
        """Counting past it would mint an id somebody else already used."""
        path = self.tree / ".slipwai/logs/ordering/ORD.jsonl"
        path.write_text('{"v": 1, "kind": "decision"}\nnot json\n', encoding="utf-8")
        with self.assertRaises(SystemExit) as refused:
            self.ids.next_id("decision", "ORD", "ordering")
        self.assertIn("is not JSON", str(refused.exception))

    def test_a_newer_log_format_stops_the_count_and_names_the_upgrade(self) -> None:
        path = self.tree / ".slipwai/logs/ordering/ORD.jsonl"
        path.write_text(json.dumps({"v": 2, "kind": "decision"}) + "\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as refused:
            self.ids.next_id("decision", "ORD", "ordering")
        self.assertIn("slipwai upgrade", str(refused.exception))


class VersionOneIdTest(unittest.TestCase):
    """A project that already has `D1` to `Dn` keeps them. Renumbering a shipped id is the cost the whole
    scheme exists to avoid, and every citation of one was correct when it was written."""

    def gate(self):
        path = ROOT / "assets/toolkit/scripts/check-decisions.py"
        spec = importlib.util.spec_from_file_location("decisions_gate", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
        return module

    def test_version_1s_heading_still_matches(self) -> None:
        found = self.gate().DECISION_HEADING.match("## D7 — which store")
        assert found is not None
        self.assertEqual(found.group("old"), "7")
        self.assertIsNone(found.group("fairway"))

    def test_version_2s_heading_matches_and_says_its_fairway(self) -> None:
        found = self.gate().DECISION_HEADING.match("## D-ORD-07 — which store")
        assert found is not None
        self.assertEqual(found.group("fairway"), "ORD")
        self.assertEqual(found.group("n"), "07")

    def test_a_heading_that_is_neither_is_still_refused(self) -> None:
        self.assertIsNone(self.gate().DECISION_HEADING.match("## Decision 7 — which store"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
