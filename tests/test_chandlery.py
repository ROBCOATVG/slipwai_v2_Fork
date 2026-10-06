"""Browsing the chandlery, and installing from it.

`search` and `show` are new in version 2. Version 1 had `list`, which says what is installed and what
the index happens to offer in one shape with no way to narrow it — so a person who wanted a language
had no way to find out it existed. These answer "what is there?" and "what is this one?".

They are tested against an index written here rather than a real one: what is published changes, and a
suite that asks the network is a suite that goes red for somebody else's reasons.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.cli_search import describe, haystack, latest, matches, search_lines, show_lines
from slipwai.language_index import Index, Release


def release(name: str, version: str = "1.0.0", **fragment: object) -> Release:
    whole = {"name": name, "core": ">=9.0,<10", "family": name, **fragment}
    return Release(name, version, f"https://example.invalid/{name}-{version}.tar.gz", "0" * 64, whole)


INDEX = Index(
    url="https://example.invalid/index.json",
    name="the test channel",
    releases={
        # Both releases carry the whole fragment, as a published one does: a release is the package,
        # not a diff against the one before it.
        "python": [release("python", version, description="Python, with FastAPI or nothing",
                           backends={"python": {"label": "Python — uv, ruff",
                                                "options": {"event-store": ["memory", "postgres"],
                                                            "http": ["none", "fastapi"]},
                                                "targets": ["none", "aws"]}})
                   for version in ("1.0.0", "1.1.0")],
        "go": [release("go", "2.0.0", description="Go — modules, gofmt",
                       backends={"go": {"label": "Go", "options": {"event-store": ["memory"]}}})],
        "java-spring": [release("java-spring", "1.0.0", family="java",
                                backends={"java-spring": {"framework": "spring", "label": "Spring Web"}})],
        "codegraph": [release("codegraph", "1.0.0", kind="extension", description="A local code index")],
        "empty": [],
    },
)


class LatestTest(unittest.TestCase):
    def test_the_newest_release_is_by_version_and_not_by_listing_order(self) -> None:
        found = latest(INDEX.releases["python"])
        assert found is not None
        self.assertEqual(found.version, "1.1.0")

    def test_a_name_the_index_lists_with_no_release_has_none(self) -> None:
        self.assertIsNone(latest(INDEX.releases["empty"]))


class HaystackTest(unittest.TestCase):
    """What a term may match. The useful search is by what a package *does*, not by its name."""

    def test_a_package_is_found_by_an_option_it_answers(self) -> None:
        """"postgres" means "something that will talk to Postgres for me", and the thing that knows is
        the option the package answers, not its name."""
        self.assertIn("postgres", haystack(INDEX.releases["python"][0]))

    def test_and_by_its_framework_and_its_family(self) -> None:
        found = haystack(INDEX.releases["java-spring"][0])
        self.assertIn("spring", found)
        self.assertIn("java", found)

    def test_and_by_its_description(self) -> None:
        self.assertIn("gofmt", haystack(INDEX.releases["go"][0]))


class MatchesTest(unittest.TestCase):
    def test_a_term_narrows_to_what_answers_it(self) -> None:
        self.assertEqual([r.name for r in matches(INDEX, "postgres")], ["python"])

    def test_no_term_lists_everything_the_index_has_a_release_for(self) -> None:
        self.assertEqual([r.name for r in matches(INDEX, "")],
                         ["codegraph", "go", "java-spring", "python"])

    def test_a_name_with_no_release_is_not_listed(self) -> None:
        self.assertNotIn("empty", [r.name for r in matches(INDEX, "")])

    def test_the_kind_narrows_languages_from_extensions(self) -> None:
        self.assertEqual([r.name for r in matches(INDEX, "", kind="extension")], ["codegraph"])
        self.assertNotIn("codegraph", [r.name for r in matches(INDEX, "", kind="language")])

    def test_a_package_that_does_not_say_its_kind_is_a_language(self) -> None:
        """Every package of version 1 is one, and the field arrived with extensions."""
        self.assertIn("go", [r.name for r in matches(INDEX, "", kind="language")])

    def test_the_family_narrows_to_one_language_s_frameworks(self) -> None:
        self.assertEqual([r.name for r in matches(INDEX, "", family="java")], ["java-spring"])


class SearchLinesTest(unittest.TestCase):
    def test_every_line_says_whether_it_is_installed(self) -> None:
        """The first thing a reader does with a result is work out whether they already have it."""
        for line in search_lines(INDEX, [], ""):
            with self.subTest(line=line.strip()):
                self.assertTrue("installed" in line or "available" in line, line)

    def test_a_term_nothing_matches_says_so_and_names_the_channel(self) -> None:
        said = search_lines(INDEX, [], "nothing-answers-this")
        self.assertEqual(len(said), 1)
        self.assertIn("the test channel", said[0])

    def test_an_unreachable_index_says_so_and_what_to_run_instead(self) -> None:
        said = search_lines(None, ["the index could not be reached"], "anything")
        self.assertIn("could not be reached", said[0])
        self.assertIn("list", said[-1])

    def test_a_package_with_no_description_says_what_it_offers(self) -> None:
        self.assertIn("backends:", describe(INDEX.releases["java-spring"][0]))


class ShowLinesTest(unittest.TestCase):
    def test_it_prints_the_newest_release_and_every_version_there_is(self) -> None:
        said = "\n".join(show_lines(INDEX, [], "python"))
        self.assertIn("python 1.1.0", said)
        self.assertIn("1.0.0, 1.1.0", said)

    def test_it_ends_on_the_command_that_installs_it(self) -> None:
        self.assertIn("language install python", show_lines(INDEX, [], "python")[-1])

    def test_it_says_which_keel_the_package_speaks(self) -> None:
        self.assertIn(">=9.0,<10", "\n".join(show_lines(INDEX, [], "go")))

    def test_a_package_the_index_has_not_got_points_at_search(self) -> None:
        said = show_lines(INDEX, [], "nothing-by-that-name")
        self.assertIn("search", said[0])

    def test_it_lists_each_backend_with_the_options_it_answers(self) -> None:
        said = "\n".join(show_lines(INDEX, [], "python"))
        self.assertIn("event-store", said)
        self.assertIn("fastapi", said)


class LocalIndexTest(unittest.TestCase):
    """The whole path, against an index written to disk: what `search` shows is what `install` reads."""

    def test_a_file_index_is_read_the_same_way_a_published_one_is(self) -> None:
        """`SLIPWAI_INDEX` may be a `file:` URL, which is how a private channel is tried before it is
        published and how this suite reaches an index without a network."""
        import os
        from unittest import mock

        from slipwai.language_index import READ, read_index

        with tempfile.TemporaryDirectory() as scratch:
            # `SLIPWAI_INDEX` names a channel's base, and the client appends the document's path — so
            # one base can carry languages, extensions and whatever a later kind needs.
            path = Path(scratch) / "slipwai-languages/index.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({
                "index": 1,
                "languages": {"toy": [{"version": "1.0.0", "file": "toy-1.0.0.tar.gz", "sha256": "0" * 64,
                                       "language": {"name": "toy", "core": ">=9.0,<10", "family": "toy",
                                                    "backends": {"toy-plain": {"label": "Toy",
                                                                               "targets": ["none"],
                                                                               "options": {"http": ["none"]}}}}}]},
            }), encoding="utf-8")
            READ.clear()
            with mock.patch.dict(os.environ, {"SLIPWAI_INDEX": Path(scratch).as_uri()}):
                found = read_index()
            READ.clear()
            self.assertEqual([r.name for r in matches(found, "")], ["toy"])
            self.assertIn("install       ", "\n".join(show_lines(found, [], "toy")))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
