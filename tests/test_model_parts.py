"""The parts that write the model, the frontend and the ladder's own table of stages.

`stage_models` is the one worth reading twice: it declares every rung of `/drive` and, per rung, the
role whose model runs it and what a delegate at that rung may write. It is how a project puts a bigger
model on deciding than on typing, and how a read-only stage is kept read-only.

Their suites generate a project and come back in 3.3z.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.project import biome, event_model, frontend, gitignore, stage_models


class StagesTest(unittest.TestCase):
    def test_every_stage_is_named_once(self) -> None:
        names = [stage.key for stage in stage_models.STAGES]
        self.assertEqual(len(names), len(set(names)))

    def test_the_ladder_still_has_the_rungs_the_plan_draws(self) -> None:
        """Section 5's figures are drawn from these names. A rung renamed here and not there is a
        picture that lies."""
        names = {stage.key for stage in stage_models.STAGES}
        for rung in ("example-map", "gaps", "plan", "tasks", "implement", "converge", "demo",
                     "adversary", "mutation"):
            with self.subTest(rung=rung):
                self.assertIn(rung, names)

    def test_the_two_cruise_seats_and_the_bosun_are_stages_without_being_rungs(self) -> None:
        """They are stages so the model table names their model and the benchmark records their cost."""
        names = {stage.key for stage in stage_models.STAGES}
        self.assertLessEqual({"skipper", "hand", "bosun"}, names)

    def test_a_read_only_stage_writes_nothing(self) -> None:
        """`gaps` and `adversary` report; a reporting stage that can write is a reviewer that edits."""
        for stage in stage_models.STAGES:
            if stage.key in ("gaps", "adversary"):
                with self.subTest(stage=stage.key):
                    self.assertEqual(stage.writes, stage_models.NONE)

    def test_every_stage_has_a_role_the_table_can_resolve(self) -> None:
        for stage in stage_models.STAGES:
            with self.subTest(stage=stage.key):
                self.assertTrue(stage.role)

    def test_the_skipper_has_a_role_of_its_own(self) -> None:
        """So a project can put a bigger model on deciding than on driving, without moving every
        judgement stage with it."""
        seats = {stage.key: stage.role for stage in stage_models.STAGES}
        self.assertEqual(seats["skipper"], stage_models.SKIPPER)
        self.assertNotEqual(seats["skipper"], stage_models.DEFAULT_ROLE)


class GitignoreTest(unittest.TestCase):
    def test_the_canonical_slots_are_the_spec_kit_files_a_slice_fills(self) -> None:
        self.assertIn("plan.md", gitignore.CANONICAL_SLOTS)
        self.assertIn("tasks.md", gitignore.CANONICAL_SLOTS)

    def test_every_harness_directory_is_projected_from_the_registry_and_not_a_fixed_list(self) -> None:
        """A harness added to the registry must not need an edit here to have its directory ignored."""
        self.assertEqual(gitignore.harness_directories({}), [])
        self.assertTrue(gitignore.projection_artifacts().strip())


class FrontendTest(unittest.TestCase):
    def test_a_browser_app_with_no_feature_still_gets_a_manifest(self) -> None:
        written = frontend.web_package_json('{"name": "web", "dependencies": {}}', set())
        self.assertIn("web", written)

    def test_a_feature_adds_to_the_manifest_and_to_the_lock_suffix(self) -> None:
        """The two move together: a dependency in one and not the other is an install that drifts."""
        features = set(frontend.WEB_LOCK_FEATURES[:1])
        if features:
            self.assertNotEqual(frontend.web_lock_suffix(features), frontend.web_lock_suffix(set()))


class BiomeTest(unittest.TestCase):
    def test_the_version_is_a_placeholder_the_workspace_answer_fills_in(self) -> None:
        """The keel does not pin the formatter; the language package that answers the workspace does."""
        self.assertTrue(biome.VERSION.startswith("__") and biome.VERSION.endswith("__"))

    def test_a_project_with_no_application_gets_no_formatter_files(self) -> None:
        self.assertEqual(biome.biome_files([]), {})


class EventModelTest(unittest.TestCase):
    def test_the_model_page_url_is_built_from_the_project_name(self) -> None:
        self.assertIn("demo", event_model.event_model_page_url("demo"))

    def test_the_workflow_calls_the_make_it_is_given(self) -> None:
        """An adopted repository may drive its gate with something other than `make`."""
        self.assertIn("just", event_model.event_model_workflow("just"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
