"""The first group of parts, each held to its own mechanism rather than to any language's answer.

These modules write pieces of a generated repository. In the experiment they were tested by generating a
project and reading what came out, which needs the scaffold — and several were tested against what `go`
and `java` in particular produce, which is now each package's CI to prove and not the keel's: a keel
whose gate asserts how Go prunes is a keel that cannot be changed without Go.

So what is here is the mechanism with the language taken out. A row of the wrong shape is refused
whoever wrote it; a marked region is replaceable whatever is inside it; the keel names no backend.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.project import ci_services, compose, entry_stores, flag_route, flags, provisioning, pruner
from slipwai.registry import load
from slipwai.services import App

EMPTY = load([])


class PrunerTest(unittest.TestCase):
    """The keel's copy of the pruner, with each loaded family's rows written into it."""

    def test_a_family_no_package_declares_has_no_rows(self) -> None:
        self.assertIsNone(pruner.family_rows(EMPTY, "a-family-nothing-declares"))

    def test_an_empty_keel_emits_the_script_with_no_rows_rather_than_no_script(self) -> None:
        """A generated project gets a working pruner whether or not a language was installed."""
        emitted = pruner.emitted([])
        self.assertIn("ROWS", emitted)
        self.assertGreater(len(emitted.splitlines()), 100)

    def test_the_rows_line_it_replaces_is_in_the_script_it_reads(self) -> None:
        """If the pruner's own text changes shape, the substitution silently writes nothing."""
        self.assertIn(pruner.ROWS_LINE, pruner.SOURCE.read_text(encoding="utf-8"))

    def test_the_rows_of_no_family_are_empty_and_not_missing(self) -> None:
        self.assertEqual(pruner.prune_rows([]), {})


class MarkedRegionTest(unittest.TestCase):
    """A marked region is how a generated file stays editable by both the keel and a person: the keel
    rewrites between the markers and never outside them."""

    def test_a_marked_body_carries_its_markers(self) -> None:
        marked = entry_stores.marked("the body")
        self.assertIn("the body", marked)
        self.assertNotEqual(marked, "the body")

    def test_each_comment_syntax_marks_the_same_body_its_own_way(self) -> None:
        """A marker written with `#` in a YAML file and `//` in a TypeScript one is the same region."""
        body = "x = 1"
        shapes = {entry_stores.marked(body), entry_stores.hash_marked(body), entry_stores.tab_marked(body)}
        self.assertEqual(len(shapes), 3)
        for shape in shapes:
            self.assertIn(body, shape)

    def test_the_feature_placeholder_is_distinctive_enough_not_to_occur_by_accident(self) -> None:
        self.assertTrue(entry_stores.FEATURE.startswith("__") and entry_stores.FEATURE.endswith("__"))


class FlagsTest(unittest.TestCase):
    """Which flag reader a backend gets, and where the keel refuses to guess."""

    def test_a_backend_no_package_answers_for_has_no_reader(self) -> None:
        with self.assertRaises(KeyError):
            flags.reader_of("a-backend-no-package-declares")

    def test_the_package_placeholder_is_replaced_and_not_shipped(self) -> None:
        self.assertEqual(flags.PACKAGE, "<package>")

    def test_the_wiring_placeholders_are_all_distinct(self) -> None:
        marks = (flag_route.IMPORT, flag_route.SOURCE, flag_route.ARGUMENT)
        self.assertEqual(len(set(marks)), len(marks))


class ComposeTest(unittest.TestCase):
    """What a project's `compose.yml` holds, which is only the services something actually needs."""

    def test_a_project_with_no_application_composes_nothing(self) -> None:
        self.assertFalse(compose.composed([]))

    def test_the_container_address_is_the_one_the_project_reads_from_its_environment(self) -> None:
        variable, url = compose.CONTAINER_ADDRESSES["postgres"]
        self.assertEqual(variable, "DATABASE_URL")
        self.assertIn("postgres:5432", url)


class CiServicesTest(unittest.TestCase):
    def test_every_ci_service_is_named_once(self) -> None:
        self.assertEqual(len(ci_services.CI_SERVICES), len(set(ci_services.CI_SERVICES)))


class ProvisioningTest(unittest.TestCase):
    def test_an_axis_with_nothing_to_provision_is_none_rather_than_an_empty_string(self) -> None:
        """`None` is "nothing to do"; an empty string would be written into the stack as a blank."""
        app = App(name="service", path="apps/service", kind="service",
                  language="none", framework=None, port=8080)
        self.assertIsNone(provisioning.provisioned(app, "event-store", "none"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
