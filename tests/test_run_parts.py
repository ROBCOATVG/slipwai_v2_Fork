"""The parts that write how a project is run: `/cruise`'s own settings, its CI, and `./init`.

These are the files a generated repository is operated through rather than read through, and the places
where a wrong string is silent. A `/cruise` that does not end its reply with one of the lines the runner
parses is a run the runner cannot follow; a shell argument that is not quoted is a project name that
can run a command.

Their suites generate a project and come back in 3.3z. Held here is what has to be true before one
exists.
"""
from __future__ import annotations

import json
import unittest

import checkout_packages  # noqa: F401

from slipwai.project import ci_workflows, cruise, existing, init_script, integration


class CruiseTest(unittest.TestCase):
    def test_every_line_the_runner_parses_is_declared_in_one_place(self) -> None:
        """The runner reads the last line of a reply. A line it does not know is a stalled run."""
        self.assertTrue(cruise.LAST_LINES)
        for line in cruise.LAST_LINES:
            with self.subTest(line=line):
                self.assertTrue(line.startswith("cruise: "), line)

    def test_the_lines_are_distinct(self) -> None:
        self.assertEqual(len(set(cruise.LAST_LINES)), len(cruise.LAST_LINES))

    def test_the_config_it_writes_is_json_and_says_where_it_is_explained(self) -> None:
        written = json.loads(cruise.cruise_config())
        self.assertIn("_comment", written)

    def test_a_cruise_nobody_is_reading_says_so_rather_than_appearing_to_work(self) -> None:
        self.assertIn("no outer loop is reading this", cruise.UNREAD)


class InitScriptTest(unittest.TestCase):
    """`./init` is shell, written by Python, run on a stranger's machine."""

    def test_a_value_with_a_quote_in_it_cannot_close_the_quote_around_it(self) -> None:
        """The whole of what stops a project name being a command."""
        quoted = init_script._sh_single_quote("it's; rm -rf /")
        self.assertTrue(quoted.startswith("'") and quoted.endswith("'"))
        self.assertNotIn("'it's", quoted)

    def test_an_ordinary_value_is_still_quoted(self) -> None:
        self.assertEqual(init_script._sh_single_quote("demo"), "'demo'")

    def test_the_argument_scan_names_every_axis_it_is_given(self) -> None:
        written = init_script.argument_scan(["event-store", "http"], ["codegraph"])
        for axis in ("event-store", "http"):
            with self.subTest(axis=axis):
                self.assertIn(f"--{axis}", written)

    def test_an_extension_is_taken_by_flag_and_not_by_a_name_the_script_knows(self) -> None:
        """`--extension <key>` is generic on purpose: the keys come from the catalogue, so a package
        adding one needs no edit to the shell `./init` is written as."""
        written = init_script.argument_scan(["http"], ["codegraph"])
        self.assertIn("--extension", written)
        self.assertNotIn("codegraph", written)

    def test_the_extension_menu_offers_what_the_catalogue_declares_and_not_a_fixed_list(self) -> None:
        offered = init_script.prompt_extensions({"toy": {"name": "Toy", "description": "a toy"}})
        self.assertIn("toy", offered)
        self.assertNotIn("codegraph", offered)


class CiWorkflowsTest(unittest.TestCase):
    """`toolchain_setup` asks the first service's backend for its family's answer, so it needs a loaded
    package and is proven in each package's own CI rather than here."""

    def test_the_paths_a_workflow_watches_are_listed_one_per_line(self) -> None:
        written = ci_workflows.dependency_paths(["apps/service/**", "package.json"])
        self.assertIn("apps/service/**", written)
        self.assertIn("package.json", written)


class IntegrationTest(unittest.TestCase):
    def test_a_project_with_no_service_has_no_integration_variables(self) -> None:
        self.assertEqual(integration.integration_variables([], [], []).strip(), "")


class ExistingTargetTest(unittest.TestCase):
    """The target the keel does not manage: it offers what `none` offers and provisions nothing."""

    def test_the_release_constraint_says_the_keel_does_not_manage_the_infrastructure(self) -> None:
        self.assertIn("the keel does not manage", existing.EXISTING_STAGE)

    def test_the_pages_it_adds_are_all_written(self) -> None:
        for page in (existing.EXISTING_GUIDANCE, existing.EXISTING_README):
            self.assertTrue(page.strip())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
