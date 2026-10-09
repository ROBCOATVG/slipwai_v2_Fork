"""The mock-up review: the surfaces drawn and approved before anything is modelled, charted or split.

Version 1 reached the demo of screens nobody had drawn. The `storyboard`, `find-gaps` and
`frontend-design` skills were all in the toolkit from the first commit and no stage called any of them,
which is the whole difference between a catalogue and a method. Slice 5.18 is the stage that calls them,
and what is held here is that it runs before the work is typed, that it produces something to review even
when nobody handed anything over, that every state ends up carrying a decision rather than a blank, and
that what a person approved is read by the stages after it.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import toolkit
from slipwai.project import commands, ladder

ROOT = Path(__file__).resolve().parents[1]


def headings(text: str) -> list[str]:
    """Each rung's heading, in ladder order: a rung opens `<n>. **Heading** — `."""
    return re.findall(r"^\d+\. \*\*(.+?)\*\*", text, re.MULTILINE)


class MockupReviewTest(unittest.TestCase):
    """The stage that draws and reviews a feature's surfaces before anything is typed.

    Version 1 reached the demo of screens nobody had drawn. The skills to avoid that were all in the
    toolkit and no stage called them, which is the difference between a catalogue and a method.
    """

    COMMAND = ROOT / "assets/toolkit/commands/mockups.md"

    def text(self) -> str:
        return " ".join(self.COMMAND.read_text(encoding="utf-8").split())

    def test_the_command_ships_to_both_profiles_and_is_documented(self) -> None:
        self.assertTrue(self.COMMAND.is_file())
        for profile in ("event-modelling", "standard"):
            with self.subTest(profile=profile):
                self.assertEqual(toolkit.toolkit_treatment("commands/mockups.md", profile, set()), "copied")
        for event in (True, False):
            with self.subTest(event=event):
                self.assertIn("mockups", commands.command_names(event))

    def test_the_rung_runs_before_the_work_is_typed(self) -> None:
        """After the specification and before the model or the chart. A surface nobody has seen becomes a
        read model, a route and a set of tests, and all three cost more to move than a drawing."""
        for event in (True, False):
            with self.subTest(event=event):
                written = headings(ladder.sail_ladder(event=event, apps=[], target="aws"))
                self.assertIn("Mock-up review", written)
                typed = "Event model" if event else "Split"
                self.assertLess(written.index("Product specification"), written.index("Mock-up review"))
                self.assertLess(written.index("Mock-up review"), written.index(typed))

    def test_the_researcher_asks_what_good_looks_like_and_says_what_it_drew_on(self) -> None:
        """The risk the plan's own risk table names: a generic answer a person approves because it is there."""
        text = self.text()
        for question in ("What job is the user doing", "How do comparable products do that job",
                         "Which states does every good version", "arrive already expecting"):
            with self.subTest(question=question):
                self.assertIn(question, text)
        self.assertIn("say that is what you are doing", text)

    def test_nothing_handed_over_means_it_drafts_rather_than_skips(self) -> None:
        """A feature whose mock-ups nobody drew is the case this stage exists for."""
        text = self.text()
        self.assertIn("The directory was empty", text)
        self.assertIn("There is always something to review", text)

    def test_it_loads_the_design_skill_and_not_the_code_review_one(self) -> None:
        """`web-interface-guidelines` reviews browser UI code, and a drawing is not code yet."""
        text = self.text()
        self.assertIn("skills/frontend-design/SKILL.md", text)
        self.assertIn("Do **not** load `web-interface-guidelines`", text)

    def test_the_review_is_a_stop_with_a_person_present(self) -> None:
        text = self.text()
        self.assertIn("skills/storyboard/SKILL.md", text)
        self.assertIn("skills/find-gaps/SKILL.md", text)
        self.assertIn("This is a stop, not a notification", text)

    def test_facing_a_person_the_words_are_paired_with_the_ordinary_ones(self) -> None:
        """Section 1's rule. Nobody should have to learn a vocabulary to answer a question about a screen."""
        self.assertIn("the slipwai word and the ordinary one", self.text())

    def test_every_state_is_approved_parked_or_not_applicable(self) -> None:
        """A state with no mark is a blank, and a blank reads as approved to whoever comes next."""
        text = self.text()
        for mark in ("`approved`", "`parked`", "`n/a`"):
            with self.subTest(mark=mark):
                self.assertIn(mark, text)
        self.assertIn("is not a decision, it is a blank", text)

    def test_a_feature_with_no_surface_is_a_written_answer_and_not_a_skip(self) -> None:
        text = self.text()
        self.assertIn("surfaces: none", text)
        self.assertIn("the question was asked rather than skipped", text)


class MockupReadersTest(unittest.TestCase):
    """What the approved states are for. An approval nothing downstream reads is a meeting."""

    def test_the_split_names_the_states_a_slice_delivers_and_may_not_invent_one(self) -> None:
        split = " ".join((ROOT / "assets/toolkit/skills/story-splitting/SKILL.md")
                         .read_text(encoding="utf-8").split())
        self.assertIn("Surfaces and states", split)
        self.assertIn("mockups/mock-states.md", split)
        self.assertIn("may only name a state that file marks `approved`", split)

    def test_the_example_map_takes_one_example_per_approved_state(self) -> None:
        text = " ".join((ROOT / "assets/toolkit/commands/example-map.md")
                        .read_text(encoding="utf-8").split())
        self.assertIn("**one example per approved state**", text)
        self.assertIn("A state marked `parked` is not mapped", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
