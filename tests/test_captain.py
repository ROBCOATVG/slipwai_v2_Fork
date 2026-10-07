"""The captain: what it claims, what it watches, and what parks it.

The one thing proved here over and over is the inversion the first attempt lacked: the captain believes the
deck log and nothing else. A fake `/drive` that writes the expected lines gets a slice through; a fake that
writes nothing is ended and parked, however alive its process is.

It runs inside a generated project, so it is run here as a script against a directory laid out like one.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"
CARRIED = ("captain.py", "clearance.py", "inbox.py", "logs.py", "berths.py", "ids.py")
CHART = """slices:
  ORD-01:
    fairway: ORD
    sets: [Placed]
    steers_by: []
  ORD-02:
    fairway: ORD
    sets: [Paid]
    steers_by: [Placed]
  BIL-01:
    fairway: BIL
    sets: [Charged]
    steers_by: [Paid]
"""
#: A fake `/drive`: writes the lines a real one would, then exits. Its argv is `<slice> <fairway>`.
WORKS = """import sys, json, pathlib, datetime
slice_id, fairway = sys.argv[1], sys.argv[2]
path = pathlib.Path(".slipwai/logs/ordering") / (fairway + ".jsonl")
path.parent.mkdir(parents=True, exist_ok=True)
now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
with path.open("a", encoding="utf-8") as handle:
    for body in ({"kind": "mark-set", "fairway": fairway, "slice": slice_id, "mark": "Placed"},
                 {"kind": "demo", "fairway": fairway, "slice": slice_id, "verdict": "accepted"}):
        handle.write(json.dumps({"v": 1, "t": now, **body}) + "\\n")
"""
#: A fake that is alive and writing nothing, which is the failure that cost the first attempt seventeen
#: iterations and which looks identical from outside to one that is working hard.
SILENT = "import time\ntime.sleep(600)\n"


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        for name in CARRIED:
            (place / name).write_text((AGENTS / name).read_text(encoding="utf-8"), encoding="utf-8")
        self.script = place / "captain.py"
        (self.root / "specs/ordering").mkdir(parents=True)
        (self.root / "specs/ordering/chart.yaml").write_text(CHART, encoding="utf-8")
        self.budget(minutes=5)

    def budget(self, minutes: float) -> None:
        (self.root / "harbour.json").write_text(
            json.dumps({"stages": {"default": {"minutes": minutes, "tokens": 400}}}), encoding="utf-8")

    def drive(self, body: str) -> str:
        path = self.root / "fake-drive.py"
        path.write_text(body, encoding="utf-8")
        return f"{sys.executable} {path}"

    def captain(self, fairway: str, drive: str, timeout: float = 90) -> subprocess.CompletedProcess:
        import os
        return subprocess.run([sys.executable, str(self.script), fairway, "--once"],
                              capture_output=True, text=True, cwd=self.root, timeout=timeout,
                              env={**os.environ, "SLIPWAI_DRIVE": drive})

    def deck(self, fairway: str, *entries: logs.Entry) -> None:
        path = self.root / logs.deck_path("ordering", fairway)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())

    def read(self, fairway: str) -> list[logs.Entry]:
        path = self.root / logs.deck_path("ordering", fairway)
        if not path.is_file():
            return []
        return logs.fold(path.read_text(encoding="utf-8").splitlines())


class ChoosingTest(Fixture):
    def test_it_claims_the_first_slice_of_its_own_fairway(self) -> None:
        done = self.captain("ORD", self.drive(WORKS))
        self.assertEqual(done.returncode, 0, done.stderr)
        claimed = [e.fields["slice"] for e in self.read("ORD") if e.kind == "claimed"]
        self.assertEqual(claimed, ["ORD-01"])

    def test_it_never_claims_another_fairway_s_slice(self) -> None:
        self.captain("ORD", self.drive(WORKS))
        self.assertEqual([e.fields["slice"] for e in self.read("ORD") if e.kind == "claimed"], ["ORD-01"])

    def test_a_slice_whose_mark_is_unset_is_waited_on_and_said(self) -> None:
        """A sibling unblocks by having planned, not by having merged — so BIL waits on Paid being set."""
        done = self.captain("BIL", self.drive(WORKS))
        self.assertIn("BIL-01 waits on", done.stdout)
        self.assertIn("Paid", done.stdout)

    def test_a_mark_set_by_a_sibling_clears_it_without_a_merge(self) -> None:
        """The whole of the parallelism: the clearing line is written at the setting slice's first stage."""
        self.deck("ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-02", mark="Paid"))
        done = self.captain("BIL", self.drive(WORKS))
        self.assertIn("BIL-01", done.stdout)
        self.assertIn("harbourmaster", done.stdout)

    def test_a_claimed_slice_is_not_claimed_twice(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))
        done = self.captain("ORD", self.drive(WORKS))
        self.assertIn("ORD-02", done.stdout)

    def test_a_parked_fairway_stays_parked_and_says_why(self) -> None:
        """A captain that quietly carried on past a park would be the status field all over again."""
        self.deck("ORD", logs.entry("parked", fairway="ORD", why="a person has to look at this"))
        done = self.captain("ORD", self.drive(WORKS))
        self.assertIn("is parked", done.stdout)
        self.assertIn("a person has to look", done.stdout)
        self.assertEqual([e for e in self.read("ORD") if e.kind == "claimed"], [])

    def test_a_fairway_the_chart_does_not_name_is_said_rather_than_guessed_at(self) -> None:
        done = self.captain("NOPE", self.drive(WORKS))
        self.assertIn("no slices", done.stdout)


class WatchingTest(Fixture):
    def test_a_drive_that_writes_nothing_is_ended_and_parked_with_the_reason(self) -> None:
        """Not because the agent said it was stuck — a stuck agent cannot say so — but because the log stopped."""
        self.budget(minutes=0.05)
        done = self.captain("ORD", self.drive(SILENT), timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        parked = [e for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parked), 1)
        self.assertIn("made no progress", str(parked[0].fields["why"]))

    def test_a_drive_that_writes_lines_is_not_ended(self) -> None:
        self.budget(minutes=0.05)
        keeps_writing = """import sys, json, pathlib, datetime, time
fairway = sys.argv[2]
path = pathlib.Path(".slipwai/logs/ordering") / (fairway + ".jsonl")
path.parent.mkdir(parents=True, exist_ok=True)
for n in range(4):
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"v": 1, "t": now, "kind": "heartbeat", "fairway": fairway}) + "\\n")
    time.sleep(1)
"""
        done = self.captain("ORD", self.drive(keeps_writing), timeout=120)
        self.assertEqual([e for e in self.read("ORD") if e.kind == "parked"], [], done.stdout)

    def test_a_drive_that_fails_parks_with_what_it_exited(self) -> None:
        self.captain("ORD", self.drive("import sys\nsys.exit(3)\n"))
        parked = [e for e in self.read("ORD") if e.kind == "parked"]
        self.assertIn("exited 3", str(parked[0].fields["why"]))


class MergeTest(Fixture):
    def test_the_merge_is_asked_of_the_harbourmaster_and_never_done(self) -> None:
        """A captain holds no credential: a berth with a token in it is a sandbox with a way out."""
        self.captain("ORD", self.drive(WORKS))
        asked = [e for e in self.read("ORD") if e.kind == "request"]
        self.assertEqual(len(asked), 1)
        self.assertEqual(asked[0].fields["what"], "merge")
        self.assertEqual(asked[0].fields["id"], "merge-ORD-01")

    def test_an_unanswered_message_from_a_person_parks_the_fairway_at_the_boundary(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", message="stop and talk to me",
                                    t="2020-01-01T00:00:00Z"))
        self.captain("ORD", self.drive(WORKS))
        parked = [e for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parked), 1)
        self.assertEqual([e for e in self.read("ORD") if e.kind == "request"], [])


class LogTest(Fixture):
    def test_a_deck_log_it_cannot_read_stops_it_rather_than_being_carried_past(self) -> None:
        """The log is the state. Carrying on past a line nobody can read is answering wrongly."""
        path = self.root / logs.deck_path("ordering", "ORD")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json\n", encoding="utf-8")
        done = self.captain("ORD", self.drive(WORKS))
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("cannot be read", done.stderr)


if __name__ == "__main__":
    unittest.main()
