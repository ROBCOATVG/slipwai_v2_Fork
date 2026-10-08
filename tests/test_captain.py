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
#: The chart these tests run against, as data, so the fake `/drive` below sets the marks this says it does.
#: They were two copies and the fake set `Placed` whatever it was driving, which passed only because the
#: captain did not read the chart's `sets` — exactly the gap slice 7.8 closes.
SLICES: dict[str, tuple[str, list[str], list[str]]] = {
    "ORD-01": ("ORD", ["Placed"], []),
    "ORD-02": ("ORD", ["Paid"], ["Placed"]),
    "BIL-01": ("BIL", ["Charged"], ["Paid"]),
    # A slice that publishes nothing: its whole gate is the demo, which is the one-rule case and not a
    # special one.
    "BIL-02": ("BIL", [], ["Charged"]),
}
CHART = "slices:\n" + "".join(
    f"  {slice_id}:\n    fairway: {fairway}\n    sets: [{', '.join(sets)}]\n"
    f"    steers_by: [{', '.join(steers)}]\n"
    for slice_id, (fairway, sets, steers) in SLICES.items())


def fake_drive(verdict: str = "accepted", marks: bool = True, demo: bool = True) -> str:
    """A fake `/drive`, as the real one is seen from here: a process that writes lines and exits.

    Its argv is `<slice> <fairway>`. What it writes is what the chart says that slice publishes, so a fake
    that is right about one slice is right about all of them.
    """
    table = {slice_id: sets for slice_id, (_f, sets, _s) in SLICES.items()}
    return f"""import sys, json, pathlib, datetime
slice_id, fairway = sys.argv[1], sys.argv[2]
path = pathlib.Path(".slipwai/logs/ordering") / (fairway + ".jsonl")
path.parent.mkdir(parents=True, exist_ok=True)
now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
lines = []
if {marks!r}:
    lines += [{{"kind": "mark-set", "fairway": fairway, "slice": slice_id, "mark": mark}}
              for mark in {table!r}[slice_id]]
if {demo!r}:
    lines.append({{"kind": "demo", "fairway": fairway, "slice": slice_id, "verdict": {verdict!r}}})
with path.open("a", encoding="utf-8") as handle:
    for body in lines:
        handle.write(json.dumps({{"v": 1, "t": now, **body}}) + "\\n")
"""


WORKS = fake_drive()
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
        # It parks, but on the gate rather than on the watch: this fake writes a line every second and
        # never the ones that close a slice. The assertion is about the watcher, so it is about the
        # watcher's own reason.
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertNotIn("the stage was ended", " ".join(parked), done.stdout)

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


class GateTest(Fixture):
    """What closes a slice: every mark the chart says it sets, and a demo, written during this turn.

    This is the fault that started slice 7.8. In the first real run `/drive` printed a help message, exited
    0, and the captain wrote `claimed`, then `request: merge`, and said the slice was through its gate —
    with nothing else in the log at all.
    """

    def attempts(self, many: int) -> None:
        held = json.loads((self.root / "harbour.json").read_text(encoding="utf-8"))
        (self.root / "harbour.json").write_text(json.dumps({**held, "attempts": many}), encoding="utf-8")

    def test_a_drive_that_exits_cleanly_having_written_nothing_parks_and_asks_for_no_merge(self) -> None:
        done = self.captain("ORD", self.drive("import sys\nsys.exit(0)\n"))
        self.assertEqual([e for e in self.read("ORD") if e.kind == "request"], [], done.stdout)
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parked), 1)
        self.assertIn("Placed", parked[0])

    def test_a_demo_with_no_mark_set_parks_naming_the_mark_the_chart_promised(self) -> None:
        done = self.captain("ORD", self.drive(fake_drive(marks=False)))
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertIn("sets Placed", parked[0], done.stdout)
        self.assertIn("no `mark-set` for Placed", parked[0])

    def test_a_mark_set_with_no_demo_parks_saying_nobody_watched_it(self) -> None:
        done = self.captain("ORD", self.drive(fake_drive(demo=False)))
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertIn("no `demo` line", parked[0], done.stdout)

    def test_a_slice_that_sets_no_mark_passes_on_its_demo_alone(self) -> None:
        """One rule, not a special case: every mark in `sets`, which is vacuous when that is empty."""
        self.deck("BIL", logs.entry("mark-set", fairway="BIL", slice="BIL-01", mark="Charged"),
                  logs.entry("claimed", fairway="BIL", slice="BIL-01"))
        done = self.captain("BIL", self.drive(WORKS))
        self.assertIn("BIL-02", done.stdout)
        self.assertIn("harbourmaster", done.stdout)

    def test_the_lines_have_to_be_this_turn_s(self) -> None:
        """Without it a retry passes on the previous turn's lines, which is the same fault as a cursor that
        outlives its log: a reader reporting a run that did not happen."""
        self.deck("ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"),
                  logs.entry("demo", fairway="ORD", slice="ORD-01", verdict="accepted"))
        done = self.captain("ORD", self.drive("import sys\nsys.exit(0)\n"))
        self.assertEqual([e for e in self.read("ORD") if e.kind == "request"], [], done.stdout)
        self.assertEqual(len([e for e in self.read("ORD") if e.kind == "parked"]), 1)

    def test_a_demo_sent_back_is_driven_again_rather_than_parked(self) -> None:
        """The person who sent it back is present and has just written notes. Parking would ask them to come
        back and restart a fairway before anything acted on them."""
        once = f"""import pathlib
tried = pathlib.Path("tried")
first = not tried.is_file()
tried.write_text("x")
exec({fake_drive("behaviour")!r} if first else {fake_drive()!r})
"""
        done = self.captain("ORD", self.drive(once))
        verdicts = [e.fields["verdict"] for e in self.read("ORD") if e.kind == "demo"]
        self.assertEqual(verdicts, ["behaviour", "accepted"], done.stdout)
        self.assertEqual(len([e for e in self.read("ORD") if e.kind == "request"]), 1)

    def test_a_demo_sent_back_past_the_bound_parks_naming_the_verdict_and_the_count(self) -> None:
        self.attempts(1)
        done = self.captain("ORD", self.drive(fake_drive("implementation")))
        self.assertEqual(len([e for e in self.read("ORD") if e.kind == "demo"]), 2, done.stdout)
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertIn("implementation", parked[0])
        self.assertIn("2 time(s)", parked[0])

    def test_attempts_of_zero_is_one_run_and_no_retry(self) -> None:
        self.attempts(0)
        self.captain("ORD", self.drive(fake_drive("behaviour")))
        self.assertEqual(len([e for e in self.read("ORD") if e.kind == "demo"]), 1)


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
