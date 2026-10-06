"""The parts that write the ladder into a generated project: its settings, its stages, its boards.

Every one of these returns prose that ends up in a page an agent reads, and in the experiment each was
tested by generating a project and reading the page back — which needs the scaffold, so those suites
return in slice 3.3z. What is held here is what the prose has to say whatever project it lands in.

`drive_settings` gets the most attention, because it carries the two widths the delivery loop is
actually driven by: how much one implementation delegate is handed, and how many failing tests a
red-green-refactor cycle opens with. Section 5 of the plan calls example mapping and that cycle the two
things both profiles share and neither optional; this is the file that writes them down.
"""
from __future__ import annotations

import json
import unittest

import checkout_packages  # noqa: F401

from slipwai.project import (
    adversary,
    agent_targets,
    demo_stop,
    docs_index,
    drive_settings,
    evolving,
    parallel_slices,
)


class DriveSettingsTest(unittest.TestCase):
    def test_the_two_widths_are_the_ones_the_loop_is_driven_by(self) -> None:
        self.assertEqual(drive_settings.DELEGATES, ("story", "rule", "task"))
        self.assertEqual(drive_settings.CYCLES, ("rule", "example"))

    def test_a_story_is_never_a_cycle(self) -> None:
        """Every rule of a story red before any is implemented is a batch. `rule` is the widest cycle."""
        self.assertIn("story", drive_settings.DELEGATES)
        self.assertNotIn("story", drive_settings.CYCLES)

    def test_the_defaults_are_the_widest_delegate_and_the_widest_legal_cycle(self) -> None:
        self.assertEqual((drive_settings.DEFAULT_DELEGATE, drive_settings.DEFAULT_CYCLE), ("story", "rule"))
        self.assertIn(drive_settings.DEFAULT_DELEGATE, drive_settings.DELEGATES)
        self.assertIn(drive_settings.DEFAULT_CYCLE, drive_settings.CYCLES)

    def test_the_written_config_is_json_carrying_both_widths_and_where_they_are_explained(self) -> None:
        written = json.loads(drive_settings.drive_config())
        self.assertEqual(written["delegate"], drive_settings.DEFAULT_DELEGATE)
        self.assertEqual(written["cycle"], drive_settings.DEFAULT_CYCLE)
        self.assertIn("RED-GREEN-REFACTOR", written["_comment"])

    def test_the_comment_names_the_command_that_changes_it(self) -> None:
        """A settings file a reader cannot change safely is a settings file they will edit by hand."""
        self.assertIn("/drive-settings", drive_settings.COMMENT)
        self.assertIn(drive_settings.SCRIPT, drive_settings.COMMENT)


class StagePagesTest:
    """Shared by the pages that read differently on the two profiles."""

    def both(self, write) -> tuple[str, str]:
        return write(True), write(False)


class ProfileTest(unittest.TestCase, StagePagesTest):
    def test_the_demo_stop_differs_by_profile_and_says_something_either_way(self) -> None:
        event, standard = self.both(demo_stop.demo_stop)
        for page in (event, standard):
            self.assertGreater(len(page.splitlines()), 3)
        self.assertNotEqual(event, standard)

    def test_the_demo_board_names_where_its_rows_come_from(self) -> None:
        event, standard = self.both(demo_stop.board_sources)
        self.assertNotEqual(event, standard)

    def test_the_adversary_command_is_written_for_both_profiles(self) -> None:
        event, standard = self.both(adversary.adversary_command)
        for page in (event, standard):
            self.assertTrue(page.strip())

    def test_a_slice_is_done_by_a_marker_each_profile_can_actually_read(self) -> None:
        event, standard = self.both(parallel_slices.done_marker)
        self.assertNotEqual(event, standard)


class PagesTest(unittest.TestCase):
    def test_the_docs_index_lists_the_files_it_is_given_and_nothing_else(self) -> None:
        index = docs_index.docs_index({"docs/design.md": "x", "docs/architecture.md": "y"})
        self.assertIn("design.md", index)
        self.assertIn("architecture.md", index)
        self.assertNotIn("nothing-here.md", index)

    def test_an_index_of_no_files_is_still_a_page(self) -> None:
        self.assertTrue(docs_index.docs_index({}).strip())

    def test_the_pages_that_take_nothing_still_write_something(self) -> None:
        for write in (evolving.evolving_page, agent_targets.agent_targets):
            with self.subTest(page=write.__name__):
                self.assertGreater(len(write().splitlines()), 3)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
