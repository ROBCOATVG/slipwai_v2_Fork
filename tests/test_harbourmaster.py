"""The harbourmaster: what reaches the harbour log, which berth a fairway gets, and what is never done.

It runs inside a generated project, so it is run here the way a project runs it — as a script, against a
directory laid out the way a project is — rather than imported into the keel's process.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"


class Fixture(unittest.TestCase):
    """A project laid out the way a generated one is, with the three scripts in it.

    A mixin rather than a base other cases inherit tests from: a subclass of a case re-runs every test in
    it, which costs a second a time and makes a failure appear three times under three names.
    """

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        for name in ("harbourmaster.py", "logs.py", "berths.py", "telegraph.py"):
            (place / name).write_text((AGENTS / name).read_text(encoding="utf-8"), encoding="utf-8")
        self.script = place / "harbourmaster.py"

    def deck(self, feature: str, fairway: str, *entries: logs.Entry) -> Path:
        path = self.root / logs.deck_path(feature, fairway)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())
        return path

    def run_once(self) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.script), "--once", "--no-fetch"],
                              capture_output=True, text=True, cwd=self.root)

    def harbour(self) -> list[logs.Entry]:
        path = self.root / logs.HARBOUR
        if not path.is_file():
            return []
        return logs.fold(path.read_text(encoding="utf-8").splitlines(), harbour=True)

class HarbourTest(Fixture):
    def test_two_captains_marks_reach_each_other_through_the_harbour_log(self) -> None:
        """The slice's whole point: a fairway reads one file, not every other fairway's."""
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        self.deck("billing", "BIL", logs.entry("mark-set", fairway="BIL", slice="BIL-01", mark="Charged"))
        self.assertEqual(self.run_once().returncode, 0)
        marks = [(e.fields["fairway"], e.fields["mark"]) for e in self.harbour() if e.kind == "mark-set"]
        self.assertEqual(sorted(marks), [("BIL", "Charged"), ("ORD", "Placed")])

    def test_a_line_no_other_fairway_needs_stays_in_its_own_log(self) -> None:
        """The harbour log is read on every turn by every captain: a line nobody needs is one everybody pays for."""
        self.deck("ordering", "ORD", logs.entry("heartbeat", fairway="ORD"),
                  logs.entry("told", fairway="ORD", message="anything"))
        self.run_once()
        self.assertEqual(self.harbour(), [])

    def test_a_park_is_carried_because_it_is_what_a_sibling_waits_on(self) -> None:
        self.deck("ordering", "ORD", logs.entry("parked", fairway="ORD", why="the gate stayed red"))
        self.run_once()
        parks = [e for e in self.harbour() if e.kind == "park"]
        self.assertEqual(parks[0].fields["why"], "the gate stayed red")

    def test_a_second_pass_carries_nothing_twice(self) -> None:
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        self.run_once()
        self.run_once()
        self.assertEqual(len([e for e in self.harbour() if e.kind == "mark-set"]), 1)

    def test_a_line_written_after_a_pass_is_carried_by_the_next(self) -> None:
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        self.run_once()
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-02", mark="Paid"))
        self.run_once()
        self.assertEqual(len([e for e in self.harbour() if e.kind == "mark-set"]), 2)

    def test_one_fairway_writing_a_bad_line_does_not_stop_the_others_being_heard(self) -> None:
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        (self.root / logs.deck_path("billing", "BIL")).parent.mkdir(parents=True, exist_ok=True)
        (self.root / logs.deck_path("billing", "BIL")).write_text("not json\n", encoding="utf-8")
        done = self.run_once()
        self.assertEqual(done.returncode, 0)
        self.assertIn("cannot be read", done.stderr)
        self.assertEqual(len([e for e in self.harbour() if e.kind == "mark-set"]), 1)


class BerthTest(Fixture):
    def test_a_request_is_answered_with_an_allocation(self) -> None:
        self.deck("ordering", "ORD", logs.entry("berth-request", fairway="ORD"))
        self.run_once()
        found = [e for e in self.harbour() if e.kind == "berth-allocated"]
        self.assertEqual(found[0].fields["fairway"], "ORD")
        self.assertEqual(found[0].fields["berth"], "ord")

    def test_two_fairways_never_get_one_block(self) -> None:
        from slipwai.berths import allocate, collisions
        self.deck("ordering", "ORD", logs.entry("berth-request", fairway="ORD"))
        self.deck("billing", "BIL", logs.entry("berth-request", fairway="BIL"))
        self.run_once()
        names = [str(e.fields["berth"]) for e in self.harbour() if e.kind == "berth-allocated"]
        self.assertEqual(len(set(names)), 2)
        self.assertEqual(collisions(allocate(names)), [])

    def test_a_restart_does_not_allocate_a_block_twice(self) -> None:
        """The cursor is a bookmark; what was allocated is read back out of the harbour log itself."""
        self.deck("ordering", "ORD", logs.entry("berth-request", fairway="ORD"))
        self.run_once()
        (self.root / ".slipwai/harbourmaster.json").unlink()
        self.deck("billing", "BIL", logs.entry("berth-request", fairway="BIL"))
        self.run_once()
        names = [str(e.fields["berth"]) for e in self.harbour() if e.kind == "berth-allocated"]
        self.assertEqual(sorted(set(names)), ["bil", "ord"])


class RequestTest(Fixture):
    def ask(self, detail: str, what: str = "push") -> list[logs.Entry]:
        self.deck("ordering", "ORD",
                  logs.entry("request", fairway="ORD", id="r1", what=what, detail=detail))
        self.run_once()
        return [e for e in self.harbour() if e.kind in ("granted", "refused")]

    def test_an_ordinary_push_is_granted(self) -> None:
        found = self.ask("git push --force-with-lease=refs/heads/slice/ORD-01: origin HEAD:main")
        self.assertEqual(found[0].kind, "granted")

    def test_a_plain_force_push_is_refused_saying_what_it_would_do(self) -> None:
        found = self.ask("git push --force origin main")
        self.assertEqual(found[0].kind, "refused")
        self.assertIn("discards somebody's commits", str(found[0].fields["why"]))

    def test_every_never_is_refused_and_says_which_rule(self) -> None:
        for detail, expected in (("git reset --hard origin/main", "not yours to discard"),
                                 ("drop table orders", "destroys data"),
                                 ("rm -rf /var/data", "destroys data"),
                                 ("git filter-branch --all", "rewrites history"),
                                 ("AWS_SECRET=abc123 deploy", "secret"),
                                 ("curl --disable-tls-verification https://x", "weakens security"),
                                 ("git commit --no-verify", "skips the gate")):
            with self.subTest(detail=detail):
                self.setUp()
                found = self.ask(detail)
                self.assertEqual(found[0].kind, "refused", detail)
                self.assertIn(expected, str(found[0].fields["why"]))

    def test_an_action_nobody_wrote_down_is_refused_with_the_list(self) -> None:
        found = self.ask("anything at all", what="rewrite-history")
        self.assertEqual(found[0].kind, "refused")
        self.assertIn("push, merge, deploy, flag, publish", str(found[0].fields["why"]))

    def test_a_refusal_is_always_written_so_nobody_waits_on_silence(self) -> None:
        self.assertEqual(len(self.ask("git push --force origin main")), 1)


if __name__ == "__main__":
    unittest.main()
