"""`check-chart`, run against hand-written charts: one fixture per way a chart can be wrong.

The chart is the one file a captain and a gate both read on either profile, and every rule in the gate is
there because its absence fails quietly. A mark nobody set leaves a slice uncleared with nothing saying on
what. A mark set twice is two schemas for one name, resolved by whichever merged last. A withdrawn mark is
a contract taken from under whoever steered by it. A slice with no capability is never demoed, and a loop
that stops nobody looks exactly like a loop with nothing to show.

So each is written here as a chart that should be refused, beside one that should pass, because a gate
proven only against good input is a gate proven against nothing. The script is run the way a generated
project runs it — a subprocess, from a tree laid out like a project — rather than imported, since that is
the thing a project's `make verify` actually calls.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "assets/toolkit/scripts/check-chart.py"

WHOLE = """
v: 1
feature: ordering
fairways:
  ORD: {context: ordering, service: apps/orders, owns: [apps/orders/**]}
  BIL: {context: billing, service: apps/billing, owns: [apps/billing/**]}
marks:
  OrderPlaced: {kind: event, schema: contracts/events/OrderPlaced.json}
  InvoiceRaised: {kind: event, schema: contracts/events/InvoiceRaised.json}
slices:
  ORD-01: {fairway: ORD, capability: place-an-order, sets: [OrderPlaced], steers_by: []}
  BIL-01: {fairway: BIL, capability: bill-an-order, sets: [InvoiceRaised], steers_by: [OrderPlaced]}
"""


class ChartGateTest(unittest.TestCase):
    """Each case writes a whole project tree, because the gate reads files the chart names."""

    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts").mkdir()
        shutil.copy(GATE, self.tree / "scripts/check-chart.py")
        (self.tree / "specs/ordering").mkdir(parents=True)
        (self.tree / "contracts/events").mkdir(parents=True)
        for event in ("OrderPlaced", "InvoiceRaised"):
            (self.tree / f"contracts/events/{event}.json").write_text("{}", encoding="utf-8")

    def run_gate(self, chart: str | None = WHOLE) -> subprocess.CompletedProcess[str]:
        if chart is not None:
            (self.tree / "specs/ordering/chart.yaml").write_text(textwrap.dedent(chart).lstrip(), encoding="utf-8")
        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        return subprocess.run([sys.executable, "scripts/check-chart.py"], cwd=self.tree,
                              capture_output=True, text=True, check=False, env=environment)

    def refused_for(self, chart: str, reason: str) -> None:
        done = self.run_gate(chart)
        self.assertEqual(done.returncode, 1, f"the gate passed this chart:\n{done.stdout}")
        self.assertIn(reason, done.stderr)
        self.assertIn("Run: python3 scripts/check-chart.py", done.stderr,
                      "a refusal that does not end on the command that fixes it costs the reader a search")

    def test_a_whole_chart_passes_and_says_what_it_held(self) -> None:
        done = self.run_gate()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("2 marks", done.stdout)

    def test_no_chart_at_all_is_not_a_failure(self) -> None:
        """`make verify` runs this everywhere, including a project with no feature in flight."""
        done = self.run_gate(chart=None)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("no chart yet", done.stdout)

    def test_a_mark_whose_contract_is_not_in_the_tree_is_refused(self) -> None:
        """A promise discovered at the far end, by the fairway that believed it."""
        self.refused_for(WHOLE.replace("contracts/events/InvoiceRaised.json",
                                       "contracts/events/NotWrittenYet.json"), "which is not in the tree")

    def test_a_mark_nobody_sets_is_refused(self) -> None:
        """Otherwise the slice waits forever and nothing says on what."""
        self.refused_for(WHOLE.replace("steers_by: [OrderPlaced]", "steers_by: [ShipmentBooked]"),
                         "which no slice sets")

    def test_a_mark_two_slices_set_is_refused(self) -> None:
        """Two schemas for one name, resolved by whichever merged last."""
        self.refused_for(WHOLE.replace("sets: [InvoiceRaised]", "sets: [InvoiceRaised, OrderPlaced]"),
                         "One mark has one setter")

    def test_a_slice_with_no_capability_is_refused(self) -> None:
        """The rule added on 2026-10-07: a slice in no capability is never demoed."""
        self.refused_for(WHOLE.replace("capability: bill-an-order, ", ""), "names no `capability`")

    def test_an_untyped_mark_is_refused_before_the_rules_run(self) -> None:
        self.refused_for(WHOLE.replace("kind: event, schema:", "schema:"), "has no kind")

    def test_a_slice_in_a_fairway_the_chart_has_not_got_is_refused(self) -> None:
        self.refused_for(WHOLE.replace("fairway: BIL,", "fairway: SHP,"), "which the chart has not got")

    def test_a_missing_block_is_one_fault_and_not_five(self) -> None:
        """A malformed chart would otherwise have every rule report the same damage in its own words."""
        done = self.run_gate(WHOLE.replace("marks:", "notmarks:"))
        self.assertEqual(done.returncode, 1)
        self.assertEqual(done.stderr.count("no `marks` block"), 1)
        self.assertNotIn("which no slice sets", done.stderr)


class FrozenChartTest(unittest.TestCase):
    """The deletion rule needs a trunk to compare against, so this one builds a repository."""

    def test_a_mark_withdrawn_from_the_frozen_chart_is_refused(self) -> None:
        tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tree, True)
        (tree / "scripts").mkdir()
        shutil.copy(GATE, tree / "scripts/check-chart.py")
        (tree / "specs/ordering").mkdir(parents=True)
        (tree / "contracts/events").mkdir(parents=True)
        for event in ("OrderPlaced", "InvoiceRaised"):
            (tree / f"contracts/events/{event}.json").write_text("{}", encoding="utf-8")
        chart = tree / "specs/ordering/chart.yaml"
        chart.write_text(textwrap.dedent(WHOLE).lstrip(), encoding="utf-8")

        def git(*arguments: str) -> None:
            subprocess.run(["git", *arguments], cwd=tree, capture_output=True, text=True, check=True)

        git("init", "-q", "-b", "main")
        git("config", "user.email", "gate@example.com")
        git("config", "user.name", "gate")
        git("add", "-A")
        git("commit", "-qm", "the frozen chart")

        # Withdraw a mark and the slice that set it, so nothing else fails first.
        chart.write_text(textwrap.dedent(WHOLE).lstrip()
                         .replace("  InvoiceRaised: {kind: event, schema: contracts/events/InvoiceRaised.json}\n", "")
                         .replace("  BIL-01: {fairway: BIL, capability: bill-an-order, sets: [InvoiceRaised],"
                                  " steers_by: [OrderPlaced]}\n", ""), encoding="utf-8")
        done = subprocess.run([sys.executable, "scripts/check-chart.py"], cwd=tree,
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("was on the frozen chart and is not here now", done.stderr)
        self.assertIn("chart.d/", done.stderr)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
