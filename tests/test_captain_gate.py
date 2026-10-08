"""What closes a slice, and what gets it to trunk. The second half of the captain's suite.

Both halves are about the same inversion as `test_captain.py` — the log is the state — applied to the two
places it was not: a turn that wrote none of what closes a slice, and a merge nobody performed.
"""
from __future__ import annotations

import json
import unittest

import checkout_packages  # noqa: F401
from captain_fixture import SLICES, WORKS, Fixture, fake_drive  # noqa: F401

from slipwai import logs


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
        self.grant("BIL-02")
        done = self.captain("BIL", self.drive(WORKS))
        self.assertIn("BIL-02", done.stdout)
        self.assertIn("merged", done.stdout)

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
        self.grant("ORD-01")
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


class FixTrunkTest(Fixture):
    """A trunk this fairway reddened is worth more than any slice it could start.

    The harbourmaster wrote the `merged` line for the commit that went red, so it knows whose it was and
    sends `fix-trunk`. Captains elsewhere keep building throughout, and that work is not wasted, because a
    sibling is cleared by a mark being set and not by a merge.
    """

    def order(self, slice_id: str = "ORD-01", fairway: str = "ORD", job: str = "audit") -> None:
        self.harbour(logs.entry("fix-trunk", harbour=True, fairway=fairway, slice=slice_id,
                                commit="a1b2c3d4", job=job))

    def test_the_fix_is_taken_before_any_new_slice(self) -> None:
        """ORD-02 is what split order would give it next. The order outranks split order."""
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="a1b2c3d4"))
        self.order()
        self.grant("ORD-01")
        done = self.captain("ORD", self.drive(WORKS))
        claimed = [e.fields["slice"] for e in self.read("ORD") if e.kind == "claimed"]
        self.assertEqual(claimed[-1], "ORD-01", done.stdout)
        self.assertIn("trunk is red", done.stdout)

    def test_an_order_another_fairway_was_sent_is_not_this_one_s(self) -> None:
        self.order(slice_id="BIL-01", fairway="BIL")
        self.grant("ORD-01")
        done = self.captain("ORD", self.drive(WORKS))
        claimed = [e.fields["slice"] for e in self.read("ORD") if e.kind == "claimed"]
        self.assertEqual(claimed, ["ORD-01"], done.stdout)
        self.assertNotIn("trunk is red", done.stdout)

    def test_an_order_already_answered_by_a_later_merge_is_not_taken_again(self) -> None:
        """The fix reaches trunk the way everything else does, so the line that says any slice is done is
        the line that says this one is."""
        self.order()
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="fixed001"))
        done = self.captain("ORD", self.drive(WORKS))
        self.assertNotIn("trunk is red", done.stdout)
        # Back to split order, which here has nothing ready — `Placed` was never set, because the lines
        # above are seeded rather than driven. What matters is that it went looking rather than re-driving
        # a slice it has already fixed.
        self.assertIn("ORD-02 waits on", done.stdout)
        self.assertEqual([e.fields["slice"] for e in self.read("ORD") if e.kind == "claimed"], ["ORD-01"])


if __name__ == "__main__":
    unittest.main()
