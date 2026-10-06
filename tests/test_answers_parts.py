"""The answers tier: what a caller asked for, what the machine can do, and what a repository already is.

Four of these read a repository the keel did not make — `delivery_facts`, `wrappers`, `unlabel` and
`preflight` — and the thing they have in common is that they must be wrong quietly. A repository nobody
promised anything about will have a `deploy.sh` that deploys nothing and a `Makefile` with no targets,
and a reader that throws on one of those has stopped an adoption over a file it did not understand.

`test_convergence.py` and `test_programme.py` came whole from the experiment. `test_upgrade.py` needs
the `upgrade` verb on the command line (slice 4.6) and `test_quick_wins.py` imports the adopt suite
(slice 4.2); both come back then.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai import delivery_facts, images, preflight, unlabel, upgrade, wrappers


class ImagesTest(unittest.TestCase):
    def test_the_placeholders_are_distinct_and_unmistakable(self) -> None:
        self.assertNotEqual(images.IMAGE, images.REPOSITORY)
        for mark in (images.IMAGE, images.REPOSITORY):
            self.assertTrue(mark.startswith("__") and mark.endswith("__"))

    def test_the_builders_are_pinned_to_exact_versions(self) -> None:
        """A range here is a production image that differs between two builds of the same commit."""
        for pin in (images.PACK_VERSION, images.KO_VERSION):
            with self.subTest(pin=pin):
                self.assertRegex(pin, r"^v\d+\.\d+\.\d+$")


class UpgradeTest(unittest.TestCase):
    def test_the_package_it_upgrades_is_this_one(self) -> None:
        self.assertEqual(upgrade.PACKAGE, "slipwai")
        self.assertEqual(upgrade.INDEX_NAME, upgrade.PACKAGE)

    def test_the_index_is_https(self) -> None:
        """An upgrade is code about to run on the reader's machine."""
        for url in (upgrade.INDEX, upgrade.FORGE):
            with self.subTest(url=url):
                self.assertTrue(url.startswith("https://"), url)


class PreflightTest(unittest.TestCase):
    def test_a_target_the_keel_does_not_manage_needs_no_tool(self) -> None:
        self.assertEqual(preflight.missing_for("none"), [])

    def test_a_probe_that_names_a_command_nobody_has_answers_false(self) -> None:
        self.assertFalse(preflight.answers(("a-command-no-machine-has", "--version")))


class DeliveryFactsTest(unittest.TestCase):
    """Read off a repository nobody promised anything about, so every answer has a 'nothing' case."""

    def test_a_host_is_recognised_from_its_remote(self) -> None:
        found = dict(delivery_facts.HOST_FORGES)
        self.assertEqual(found["github.com"], "github")

    def test_the_deploy_pattern_matches_the_words_a_script_would_use(self) -> None:
        for word in ("deploy", "release", "kubectl apply"):
            with self.subTest(word=word):
                self.assertTrue(delivery_facts.DEPLOYS.search(f"it will {word} the thing"))

    def test_it_does_not_match_a_word_that_merely_contains_one(self) -> None:
        self.assertIsNone(delivery_facts.DEPLOYS.search("redeployment-free"))


class WrappersTest(unittest.TestCase):
    """Reading a command line out of somebody's build file, to know what it actually runs."""

    def test_a_command_is_split_on_every_separator_a_shell_honours(self) -> None:
        for separator in ("&&", "||", "|", ";"):
            with self.subTest(separator=separator):
                self.assertTrue(wrappers.SEPARATORS.search(f"a {separator} b"))

    def test_a_leading_assignment_is_recognised_rather_than_read_as_the_command(self) -> None:
        self.assertTrue(wrappers.ASSIGNMENT.fullmatch("JAVA_HOME=/opt/java mvn test"))
        self.assertIsNone(wrappers.ASSIGNMENT.fullmatch("mvn test"))

    def test_a_shell_builtin_is_not_a_tool_the_repository_depends_on(self) -> None:
        self.assertTrue(wrappers.BUILTINS)
        self.assertIn("cd", wrappers.BUILTINS)


class UnlabelTest(unittest.TestCase):
    """Taking the experimental label off an adopted repository's delivery section."""

    def test_the_heading_pattern_matches_the_labelled_form_only(self) -> None:
        labelled = "## Delivery method (installed by slipwai 1.5.0; experimental)"
        self.assertTrue(unlabel.HEADING.search(labelled))
        self.assertIsNone(unlabel.HEADING.search(labelled.replace("; experimental", "")))

    def test_the_marked_block_is_what_makes_the_section_replaceable(self) -> None:
        self.assertIn("extension:delivery", unlabel.BLOCK_BEGIN)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
