"""The fleet board: every column folded from the logs, and nothing kept anywhere else.

The two states it matters most to tell apart are `stalled` and `finished`, because in a status field they
look identical — neither is writing anything. The log tells them apart for nothing, which is the whole
reason `heartbeat` is a line.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import fleet, logs
from slipwai.cli_fleet import lines
from slipwai.project.harbour import harbour_config

NOW = datetime(2026, 10, 7, 12, 0, 0, tzinfo=UTC)


def when(minutes: float) -> str:
    return (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / ".slipwai").mkdir()
        (self.root / "harbour.json").write_text(harbour_config(), encoding="utf-8")

    def deck(self, fairway: str, *entries: logs.Entry, feature: str = "ordering") -> None:
        path = self.root / logs.deck_path(feature, fairway)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())

    def harbour(self, *entries: logs.Entry) -> None:
        path = self.root / logs.HARBOUR
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())

    def board(self) -> dict:
        return fleet.board(self.root, json.loads((self.root / "harbour.json").read_text()), now=NOW)


class StateTest(Fixture):
    def test_a_fairway_with_a_log_and_no_lines_is_not_started(self) -> None:
        """Not `0%` and not `working`: a fairway nobody has begun is a fact, and the board says it."""
        path = self.root / logs.deck_path("ordering", "ORD")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        self.assertEqual(self.board()["berths"][0]["state"], "not started")
        self.assertEqual(self.board()["berths"][0]["slice"], fleet.NOTHING)

    def test_a_fairway_writing_lines_is_working(self) -> None:
        self.deck("ORD", logs.entry("heartbeat", fairway="ORD", t=when(1)))
        self.assertEqual(self.board()["berths"][0]["state"], "working")

    def test_a_fairway_that_has_stopped_writing_is_stalled_and_not_finished(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(500)))
        self.assertEqual(self.board()["berths"][0]["state"], "stalled")

    def test_a_fairway_whose_last_line_is_a_merge_is_finished_and_not_stalled(self) -> None:
        """The pair that look identical in a status field, told apart by the last line for nothing."""
        self.deck("ORD",
                  logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(600)),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc123", t=when(500)))
        self.assertEqual(self.board()["berths"][0]["state"], "finished")

    def test_a_parked_fairway_says_parked_whatever_its_heartbeat(self) -> None:
        self.deck("ORD", logs.entry("heartbeat", fairway="ORD", t=when(1)),
                  logs.entry("parked", fairway="ORD", why="a person has to look", t=when(1)))
        self.assertEqual(self.board()["berths"][0]["state"], "parked")

    def test_the_slice_shown_is_the_one_claimed_and_not_yet_merged(self) -> None:
        self.deck("ORD",
                  logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(9)),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc", t=when(8)),
                  logs.entry("claimed", fairway="ORD", slice="ORD-02", t=when(7)))
        self.assertEqual(self.board()["berths"][0]["slice"], "ORD-02")


class NumbersTest(Fixture):
    def test_a_number_nobody_wrote_is_a_dash_and_not_a_zero(self) -> None:
        self.deck("ORD", logs.entry("heartbeat", fairway="ORD", t=when(1)))
        self.assertEqual(self.board()["berths"][0]["tokens"], fleet.NOTHING)
        self.assertIsNone(self.board()["bunker"]["spent"])

    def test_tokens_are_summed_from_the_lines_that_record_them(self) -> None:
        self.deck("ORD", logs.entry("heartbeat", fairway="ORD", tokens=120, t=when(2)),
                  logs.entry("heartbeat", fairway="ORD", tokens=80, t=when(1)))
        self.assertEqual(self.board()["berths"][0]["tokens"], 200)
        self.assertEqual(self.board()["bunker"]["spent"], 200)

    def test_the_telegraph_is_read_from_the_file_and_what_banked_it_from_the_log(self) -> None:
        self.harbour(logs.entry("fires-banked", harbour=True, step="slow-ahead",
                                why="the day's bunker is spent", t=when(3)))
        pressure = self.board()["pressure"]
        self.assertEqual(pressure["position"], "half-ahead")
        self.assertIn("bunker is spent", pressure["banked"])


class InboxTest(Fixture):
    def test_an_unanswered_message_is_what_the_board_leads_with(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", message="look at this", t=when(5)))
        waiting = self.board()["inbox"]
        self.assertEqual(len(waiting), 1)
        self.assertEqual(waiting[0]["what"], "look at this")
        self.assertIn("waiting on you: 1", "\n".join(lines(self.root)))

    def test_an_answered_message_is_not_waiting_on_anybody(self) -> None:
        """A `read` carries the `t` of the `told` it answers, which is what makes it a receipt."""
        self.deck("ORD", logs.entry("told", fairway="ORD", message="look at this", t=when(5)),
                  logs.entry("read", fairway="ORD", told=when(5), t=when(4)))
        self.assertEqual(self.board()["inbox"], [])

    def test_a_park_is_waiting_on_a_person_too(self) -> None:
        self.deck("ORD", logs.entry("parked", fairway="ORD", why="the gate stayed red", t=when(2)))
        self.assertEqual(self.board()["inbox"][0]["kind"], "parked")


class FeedTest(Fixture):
    def test_both_logs_are_merged_by_time(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(3)))
        self.harbour(logs.entry("telegraph", harbour=True, position="slow-ahead", t=when(2)))
        self.deck("BIL", logs.entry("claimed", fairway="BIL", slice="BIL-01", t=when(1)),
                  feature="ordering")
        self.assertEqual([who for _, who, _ in self.board()["feed"]], ["ORD", "harbour", "BIL"])


class UnreadableTest(Fixture):
    def test_a_log_that_cannot_be_read_is_said_rather_than_drawn_empty(self) -> None:
        """An empty row and an unreadable one are different facts, and drawing both the same is guessing."""
        path = self.root / logs.deck_path("ordering", "ORD")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json\n", encoding="utf-8")
        self.assertIn("ORD", self.board()["unreadable"])
        self.assertIn("cannot be read", "\n".join(lines(self.root)))


class FoldTest(Fixture):
    def test_the_board_keeps_nothing_so_a_new_line_changes_it(self) -> None:
        """Every column is computed each time: a board that cached anything could be wrong about what
        happened, and a board that can be wrong is worse than no board, because it is believed."""
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(2)))
        before = self.board()["berths"][0]["merged"]
        self.deck("ORD", logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc", t=when(1)))
        self.assertEqual((before, self.board()["berths"][0]["merged"]), (0, 1))


if __name__ == "__main__":
    unittest.main()
