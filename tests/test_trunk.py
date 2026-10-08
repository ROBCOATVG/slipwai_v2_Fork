"""Trunk's own CI, read before any merge is granted, so the fleet stops adding to a red build.

The gate before a merge is the project's `make verify`; CI runs `make ci`, which adds `audit` and
`test-integration`. So trunk can go red from a check `verify` never ran, and until this nothing noticed
while every fairway kept merging onto it.

Offline: `harbour.json`'s `ci` names the command that answers, so these cases answer it themselves rather
than asking a forge. That hook is not a test fixture — a harbour on anything but GitHub needs it — and a
suite that reached the network would be one nobody could run on a train.
"""
from __future__ import annotations

import json
import sys
import unittest

import checkout_packages  # noqa: F401
from harbourmaster_fixture import MergeFixture  # noqa: F401

from slipwai import logs


def run(conclusion: str, sha: str = "a1b2c3d4e5f6", workflow: str = "verify", status: str = "completed") -> dict:
    return {"status": status, "conclusion": conclusion, "headSha": sha,
            "workflowName": workflow, "url": f"https://forge/runs/{workflow}"}


class TrunkFixture(MergeFixture):
    """A real repository, as a merge needs, whose forge answers whatever the case says it does.

    The merge has to be able to succeed, or every case here would read `refused` for the wrong reason.
    """

    def forge_says(self, *runs: dict) -> None:
        answer = self.root / "forge.py"
        answer.write_text(f"import json\nprint(json.dumps({list(runs)!r}))\n", encoding="utf-8")
        self.harbour_config(ci=[sys.executable, str(answer)])

    def harbour_config(self, **held: object) -> None:
        (self.root / "harbour.json").write_text(json.dumps({"trunk": "main", **held}), encoding="utf-8")

    def ask_to_merge(self, slice_id: str = "ORD-01") -> None:
        self.slice_branch(slice_id, f"{slice_id}.txt", f"{slice_id}\n")
        self.ask(slice_id)

    def kinds(self) -> list[str]:
        return [entry.kind for entry in self.harbour()]

    def of_kind(self, kind: str) -> list[logs.Entry]:
        return [entry for entry in self.harbour() if entry.kind == kind]


class ReadingTest(TrunkFixture):
    def test_a_red_trunk_refuses_every_merge_and_says_which_commit_and_job(self) -> None:
        self.forge_says(run("failure", workflow="verify"))
        self.ask_to_merge()
        self.run_once()
        red = self.of_kind("trunk-red")
        self.assertEqual(len(red), 1, self.kinds())
        self.assertEqual(red[0].fields["job"], "verify")
        self.assertTrue(str(red[0].fields["commit"]).startswith("a1b2c3d4"))
        refused = self.of_kind("refused")
        self.assertEqual(len(refused), 1)
        self.assertIn("red trunk", str(refused[0].fields["why"]))

    def test_one_workflow_green_and_another_red_is_a_red_trunk(self) -> None:
        """Reading only the first run would call it green, which is the whole failure this is here to stop."""
        self.forge_says(run("success", workflow="verify"), run("failure", workflow="CodeQL"))
        self.ask_to_merge()
        self.run_once()
        self.assertEqual(self.of_kind("trunk-red")[0].fields["job"], "CodeQL")
        self.assertEqual(self.of_kind("granted"), [])

    def test_only_the_newest_commit_s_runs_are_read(self) -> None:
        """A commit that was red and has since been fixed is history, not a verdict about trunk now."""
        self.forge_says(run("success", sha="newnewnew"), run("failure", sha="oldoldold"))
        self.ask_to_merge()
        self.run_once()
        self.assertEqual(self.of_kind("trunk-red"), [], self.kinds())

    def test_a_run_still_going_is_not_a_verdict(self) -> None:
        self.forge_says(run("", status="in_progress"))
        self.ask_to_merge()
        self.run_once()
        self.assertEqual(self.of_kind("trunk-red"), [])
        self.assertEqual(self.of_kind("granted")[0].fields["ci"], "unverified")

    def test_a_forge_that_cannot_be_asked_reads_unverified_and_never_green(self) -> None:
        """A harbour with no forge has to keep working, and nobody should read the line later as a run that
        was checked."""
        self.harbour_config(ci="off")
        self.ask_to_merge()
        self.run_once()
        granted = self.of_kind("granted")
        self.assertEqual(len(granted), 1, self.kinds())
        self.assertEqual(granted[0].fields["ci"], "unverified")

    def test_a_green_trunk_grants_and_says_so(self) -> None:
        self.forge_says(run("success"))
        self.ask_to_merge()
        self.run_once()
        self.assertEqual(self.of_kind("granted")[0].fields["ci"], "green")


class SayingTest(TrunkFixture):
    def test_red_is_written_once_and_not_every_pass(self) -> None:
        """A board that said `trunk-red` every fifteen seconds is one nobody reads."""
        self.forge_says(run("failure"))
        self.run_once()
        self.run_once()
        self.assertEqual(len(self.of_kind("trunk-red")), 1, self.kinds())

    def test_green_after_red_is_written_so_the_log_says_when_the_queue_reopened(self) -> None:
        self.forge_says(run("failure"))
        self.run_once()
        self.forge_says(run("success", sha="fixedfixed"))
        self.run_once()
        self.assertEqual(len(self.of_kind("trunk-green")), 1, self.kinds())

    def test_green_that_was_always_green_says_nothing(self) -> None:
        self.forge_says(run("success"))
        self.run_once()
        self.assertEqual(self.of_kind("trunk-green"), [])


class WhoBrokeItTest(TrunkFixture):
    def test_the_fix_goes_to_the_fairway_whose_merged_line_names_that_commit(self) -> None:
        """This process wrote that line, which is the whole reason the fix can be sent anywhere at all."""
        self.deck("ordering", "ORD", logs.entry("merged", fairway="ORD", slice="ORD-01",
                                                commit="a1b2c3d4e5f6"))
        self.forge_says(run("failure", workflow="audit"))
        self.run_once()
        orders = self.of_kind("fix-trunk")
        self.assertEqual(len(orders), 1, self.kinds())
        self.assertEqual(orders[0].fields["fairway"], "ORD")
        self.assertEqual(orders[0].fields["slice"], "ORD-01")
        self.assertEqual(orders[0].fields["job"], "audit")

    def test_a_red_no_merged_line_accounts_for_parks_for_a_person_at_once(self) -> None:
        """A direct push, or a red older than any merge. Guessing who broke it would send a captain to
        rewrite somebody else's work."""
        self.forge_says(run("failure"))
        self.run_once()
        self.assertEqual(self.of_kind("fix-trunk"), [])
        parked = self.of_kind("park")
        self.assertEqual(len(parked), 1, self.kinds())
        self.assertIn("no `merged` line accounts for", str(parked[0].fields["why"]))


if __name__ == "__main__":
    unittest.main()
