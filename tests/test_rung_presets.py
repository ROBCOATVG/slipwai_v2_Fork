"""Which skills a project gets by its rung, and what the `event-modelling` constitution now says.

Three skills carried both capabilities in their frontmatter — `event-modelling` and `event-sourcing` —
and `serves()` is any-match, so every one of them shipped to every modelled project. That was right while
choosing Event Modeling chose the log with it. Phase 15 split the two, and a project whose every service
keeps current state would otherwise receive a skill telling it to rehydrate a Decider from a log it has
not got.

The constitution moved the other way: it says more now, not less. Principle III was *Event-Sourced Core
with the Decider Pattern* and read as though every service were on that rung; it is *The Rung Is Recorded
Per Service, and Event Sourcing Is the Default* — the recommendation stated as the recommendation, the
exception named and required to carry a reason, and both rungs' rules written out, because a mixed
project is the shape phase 15 exists to allow.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.assets import PROFILE_ROOT
from slipwai.capabilities import serves
from slipwai.toolkit import skill_declarations

CONSTITUTION = (
    PROFILE_ROOT / "event-modelling/.specify/presets/event-modelling"
    / "templates/constitution-template.md"
)
TASKS = PROFILE_ROOT / "event-modelling/.specify/presets/event-modelling/templates/tasks-template.md"
#: What a project on each rung can do. `event-sourcing` is brought by `write-model: events` (15.1), so a
#: project whose every service is state-stored carries the model and not the log.
SOURCED = {"event-modelling", "event-sourcing", "typescript"}
STATE_STORED = {"event-modelling", "typescript"}


class SkillsTest(unittest.TestCase):
    def declared(self, skill: str) -> tuple[str, ...] | None:
        return skill_declarations().get(skill)

    def test_the_sourcing_skill_declares_the_rung_and_not_the_profile(self) -> None:
        self.assertEqual(self.declared("event-sourcing"), ("event-sourcing",))

    def test_the_modelling_skills_declare_the_profile_and_not_the_rung(self) -> None:
        for skill in ("event-modeling", "global-event-model"):
            with self.subTest(skill=skill):
                self.assertEqual(self.declared(skill), ("event-modelling",))

    def test_a_state_stored_project_holds_the_modelling_skills(self) -> None:
        for skill in ("event-modeling", "global-event-model"):
            with self.subTest(skill=skill):
                self.assertTrue(serves(self.declared(skill), STATE_STORED))

    def test_a_state_stored_project_does_not_hold_the_sourcing_skill(self) -> None:
        """The failure this closes: a project with no log told how to rehydrate a Decider from one."""
        self.assertFalse(serves(self.declared("event-sourcing"), STATE_STORED))

    def test_an_event_sourced_project_holds_all_three(self) -> None:
        for skill in ("event-sourcing", "event-modeling", "global-event-model"):
            with self.subTest(skill=skill):
                self.assertTrue(serves(self.declared(skill), SOURCED))

    def test_a_mixed_project_holds_all_three_because_one_service_earns_it(self) -> None:
        """Capabilities are project-wide: one service on the log is enough for the project to carry it."""
        self.assertTrue(serves(self.declared("event-sourcing"), SOURCED))


class ConstitutionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = CONSTITUTION.read_text(encoding="utf-8")

    def test_the_principle_is_about_the_rung_rather_than_about_one_rung(self) -> None:
        self.assertIn("### III. The Rung Is Recorded Per Service", self.text)

    def test_event_sourcing_is_stated_as_the_default_rather_than_as_not_one(self) -> None:
        """The owner's decision of 2026-10-09: the catalogue could not express the exception, which was
        the fault; it does not follow that the two rungs meet a reader as equals."""
        self.assertIn("Event sourcing is this project's default and its recommendation", self.text)
        self.assertNotIn("not a default", self.text)

    def test_the_reason_given_is_slicing_and_changeability_rather_than_storage(self) -> None:
        self.assertIn("contract every later slice", self.text)
        self.assertIn("replay away", self.text)

    def test_choosing_the_exception_is_recorded_with_its_reason(self) -> None:
        self.assertIn("MUST NOT be event-sourced merely for", self.text)
        self.assertIn("rung nobody justified is the default", self.text)

    def test_both_rungs_rules_are_written_out(self) -> None:
        self.assertIn("**Where the rung is `events`:**", self.text)
        self.assertIn("**Where the rung is `state`:**", self.text)

    def test_the_state_rung_refuses_the_two_fields_the_gate_refuses(self) -> None:
        """The constitution and `make check-model` say the same thing, or one of them is decoration."""
        self.assertIn("MUST NOT name `guard` or `folds`", self.text)

    def test_a_command_checks_the_write_model_rather_than_the_event_stream(self) -> None:
        """Principle II named the one rung's machinery for a rule that is true of both."""
        self.assertIn("MUST check the **write model**", self.text)


class TasksTemplateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = TASKS.read_text(encoding="utf-8")

    def test_the_foundational_phase_says_which_tasks_are_one_rungs(self) -> None:
        self.assertIn("T017, T019 and T022–T027 are the event-sourced rung's", self.text)

    def test_every_event_store_task_has_a_state_stored_twin(self) -> None:
        for task in ("T017", "T019", "T022", "T023", "T024", "T025", "T026", "T027"):
            with self.subTest(task=task):
                self.assertIn(f"{task} **(state)**", self.text)

    def test_the_state_twin_names_the_version_column_as_the_concurrency_control(self) -> None:
        self.assertIn("`version` column", self.text)

    def test_the_state_twin_keeps_the_events_by_writing_them_in_the_same_transaction(self) -> None:
        """A state-stored service still raises the model's events; losing them on failure is the one
        way the rung turns into a rung that cannot be modelled."""
        self.assertIn("same transaction", self.text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
