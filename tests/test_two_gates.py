"""Two gates, not one: what an increment pays for, and what runs once before the merge.

In the first attempt one `make verify` did everything, so every increment paid for lint, typecheck,
structure and the whole suite. The owner's own note in the experiment was "use full verify sparingly, it's
heavy", which is a gate nobody runs. Theme B item 9 splits it: the fast checks per increment inside a
slice, the full gate once on the rebased branch before `main`.

A generated project needs its own `unit` for that, and which of its targets are fast is the backends' to
say rather than the keel's to assume — so `fast_targets` is a protocol member with a default that answers
every backend that has nothing to add.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.project import ladder
from slipwai.project.native_commands import DEFAULT_FAST, TARGETS, fast_targets
from slipwai.registry import FAST_TARGETS, PROTOCOL


class FastTargetsTest(unittest.TestCase):
    def test_the_member_is_declared_and_never_required(self) -> None:
        """It arrives optional because every backend already has an answer: the test target alone."""
        self.assertIn(FAST_TARGETS, PROTOCOL)
        self.assertFalse(FAST_TARGETS.required)

    def test_the_default_is_the_test_suite_alone(self) -> None:
        """Integration, mutation, the image build and the audit belong to the gate before the merge."""
        self.assertEqual(DEFAULT_FAST, ("test",))
        for slow in ("integration", "mutation", "audit"):
            with self.subTest(target=slow):
                self.assertNotIn(slow, DEFAULT_FAST)

    def test_a_project_with_no_services_still_has_an_answer(self) -> None:
        self.assertEqual(fast_targets([]), DEFAULT_FAST)

    def test_every_default_target_is_one_the_contract_names(self) -> None:
        """A fast target that is not a target is a Makefile recipe keyed on nothing."""
        for target in DEFAULT_FAST:
            with self.subTest(target=target):
                self.assertIn(target, TARGETS)


class LadderGateTest(unittest.TestCase):
    def rungs(self) -> dict[str, str]:
        import re
        written = ladder.drive_ladder(event=True, apps=[], target="aws")
        parts = re.split(r"^(?=\d+\. \*\*)", written, flags=re.MULTILINE)
        found = {}
        for part in parts:
            match = re.match(r"^\d+\. \*\*(.+?)\*\*", part)
            if match:
                found[match.group(1)] = " ".join(part.split())
        return found

    def test_the_increment_runs_the_fast_checks_and_says_the_full_gate_is_the_merge_s(self) -> None:
        implement = self.rungs()["Implementation"]
        self.assertIn("make unit", implement)
        self.assertIn("never the full gate, which belongs to the merge", implement)

    def test_only_the_merge_rung_runs_the_full_gate(self) -> None:
        """The habit version 2 drops: an increment that pays for the whole suite."""
        rungs = self.rungs()
        self.assertIn("make verify", rungs["Merge to main"])
        for heading, body in rungs.items():
            if heading in {"Merge to main", "Principles"}:
                continue
            with self.subTest(rung=heading):
                self.assertNotIn("make verify", body)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
