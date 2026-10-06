"""`AGENTS.md` carries the plan's rules, and still carries them when the plan changes.

A session reads `AGENTS.md` and nothing else before it starts work, so a rule that exists only in the plan
is a rule nobody follows. The plan's section 8 is the source; this holds the root file to it by the one
part of each rule that cannot be paraphrased away — its bold lead-in.

Unlike `GLOSSARY.md`, this file is not generated. It says more than the plan does, in a different order,
for a different reader. What is held is that no rule went missing.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
PLAN = REPOSITORY / "docs/slipwai-2-plan.md"
AGENTS = REPOSITORY / "AGENTS.md"
SECTION = "## 8. The rules for doing the work"
# `1. **Chart first.** Do not claim …` — the numbered rules of section 8, by their bold lead-in.
RULE = re.compile(r"^\d+\. \*\*(.+?)\*\*")


def rules() -> list[str]:
    lines = PLAN.read_text(encoding="utf-8").splitlines()
    start = lines.index(SECTION) + 1
    found = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        match = RULE.match(line)
        if match:
            found.append(match.group(1))
    return found


class RulesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = rules()
        self.page = AGENTS.read_text(encoding="utf-8")

    def test_the_plan_still_has_its_rules(self) -> None:
        self.assertEqual(len(self.rules), 11, f"section 8 now has {len(self.rules)} rules: {self.rules}")

    def test_every_rule_reaches_the_page_a_session_reads(self) -> None:
        for rule in self.rules:
            with self.subTest(rule=rule):
                # assertTrue rather than assertIn: a failed assertIn prints the whole page.
                self.assertTrue(rule in self.page, f"AGENTS.md does not carry the rule {rule!r}")

    def test_the_page_says_which_gate_runs_when(self) -> None:
        """The two-gate split is the rule most easily lost, because one gate is simpler to describe."""
        for command in ("make unit", "make verify", "SLOW"):
            self.assertIn(command, self.page)

    def test_the_page_names_both_source_commits(self) -> None:
        """Rule 11 is unusable without them: "bring back by name" needs a name to bring it from."""
        self.assertIn("e1a9e43", self.page)
        self.assertIn("c6f1e74", self.page)

    def test_the_page_sends_a_session_to_the_glossary_first(self) -> None:
        self.assertIn("GLOSSARY.md", self.page.split("## ")[0])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
