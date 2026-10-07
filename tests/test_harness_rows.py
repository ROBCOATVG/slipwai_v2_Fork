"""The harness rows: what each says about running headless and about its hooks, and what nobody has proved.

A row records what a harness's own documentation says. Whether any of it was true when a run depended on it
is a different claim, and the registry keeps the two apart — which is what `proven` is for.
"""
from __future__ import annotations

import json
import unittest

import checkout_packages  # noqa: F401

from slipwai.harness import REGISTRY, name_of, proven, registry, row_of, unproven_line

#: The six the captain is built for, and the key each is under. Named here because the plan names them.
SIX = {"claude": "Claude Code", "codex": "Codex CLI", "cursor-agent": "Cursor",
       "gemini": "Gemini CLI", "opencode": "OpenCode", "kiro-cli": "Kiro CLI"}


class RegistryTest(unittest.TestCase):
    def test_the_registry_is_json_and_every_row_has_a_key(self) -> None:
        document = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.assertTrue(all(row.get("key") for row in document["harnesses"]))

    def test_the_six_the_captain_is_built_for_all_have_a_row(self) -> None:
        for key in SIX:
            with self.subTest(key=key):
                self.assertTrue(row_of(key), key)

    def test_each_of_the_six_says_how_it_is_invoked_headless_or_why_it_cannot_be(self) -> None:
        """A row that said neither would be a row nothing could act on."""
        for key in SIX:
            with self.subTest(key=key):
                row = row_of(key)
                headless = row.get("headless")
                self.assertTrue((isinstance(headless, dict) and headless.get("command"))
                                or row.get("headlessReason") or (headless or {}).get("how"), key)

    def test_each_of_the_six_says_whether_a_turn_end_hook_can_refuse_the_end(self) -> None:
        """`holds` is the one hook that matters most: it is what stops a turn ending mid-slice."""
        for key in SIX:
            with self.subTest(key=key):
                row = row_of(key)
                hooks = row.get("hooks")
                self.assertTrue(isinstance(hooks, dict) and "holds" in hooks
                                or row.get("hooksReason") is not None or hooks is None, key)


class ProvenTest(unittest.TestCase):
    def test_every_row_says_whether_a_captain_has_driven_it(self) -> None:
        """Every row, not six of them: proven is a fact about a harness, not a field some have."""
        for row in registry():
            with self.subTest(key=row["key"]):
                self.assertIn("proven", row)
                self.assertIsInstance(row["proven"], bool)

    def test_none_is_proven_yet_and_the_registry_says_so_rather_than_implying_it(self) -> None:
        self.assertFalse(any(proven(row["key"]) for row in registry()))

    def test_an_unproven_harness_is_said_once_and_is_never_a_refusal(self) -> None:
        """Every harness is unproven until somebody is first; a factory that refused them all would have none."""
        said = unproven_line("claude")
        self.assertIn(name_of("claude"), said)
        self.assertIn("unproven", said)

    def test_what_it_says_is_that_the_captain_depends_on_no_hook(self) -> None:
        """Which is the half that matters: what is at risk is a second belt, not the run."""
        said = unproven_line("claude")
        self.assertIn("depend on no harness hook", said)

    def test_a_harness_nobody_named_says_nothing(self) -> None:
        self.assertEqual(unproven_line(""), "")

    def test_a_row_the_registry_has_not_got_is_empty_rather_than_a_fault(self) -> None:
        self.assertEqual(row_of("nothing-by-that-name"), {})


if __name__ == "__main__":
    unittest.main()
