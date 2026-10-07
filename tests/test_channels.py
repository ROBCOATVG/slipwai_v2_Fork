"""Several channels, read in order: an organisation's own before the public one.

Every channel here is a `file:` tree the test writes, which is how a private channel is tried before it is
published and how this suite reaches an index without a network.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai.cli_search import matches, show_lines
from slipwai.index_schema import CHANDLERY, Index
from slipwai.language_index import READ, Unreachable, bases, channels, read_index

LANGUAGE = {"name": "toy", "core": ">=9.0,<10", "family": "toy",
            "backends": {"toy-plain": {"label": "Toy", "targets": ["none"], "options": {"http": ["none"]}}}}


def channel(root: Path, names: dict[str, str]) -> str:
    """One channel serving a release of each name at the version given. Returns its base as a `file:` URL."""
    place = root / "slipwai-languages"
    place.mkdir(parents=True)
    place.joinpath("index.json").write_text(json.dumps({
        "index": 2,
        "packages": {name: [{"version": version, "file": f"{name}-{version}.tar.gz", "sha256": "0" * 64,
                             "kind": "language", "language": {**LANGUAGE, "name": name, "family": name},
                             "description": f"{name} from {root.name}"}]
                     for name, version in names.items()},
    }), encoding="utf-8")
    return root.as_uri()


class BasesTest(unittest.TestCase):
    def test_a_comma_separated_list_is_read_in_order(self) -> None:
        with mock.patch.dict(os.environ, {CHANDLERY: "https://one.invalid, https://two.invalid/"}):
            self.assertEqual(bases(), ["https://one.invalid", "https://two.invalid"])

    def test_an_empty_entry_is_dropped_rather_than_asked(self) -> None:
        with mock.patch.dict(os.environ, {CHANDLERY: "https://one.invalid,,  ,"}):
            self.assertEqual(bases(), ["https://one.invalid"])

    def test_nothing_set_is_no_channels_of_its_own(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(CHANDLERY, None)
            self.assertEqual(bases(), [])


class ChannelsTest(unittest.TestCase):
    def test_the_old_single_index_is_kept_and_kept_last(self) -> None:
        """It is the keel's own upgrade index too, so setting it meant "fetch from here", not "only here"."""
        with mock.patch.dict(os.environ, {CHANDLERY: "https://private.invalid",
                                          "SLIPWAI_INDEX": "https://public.invalid"}):
            found = channels()
        self.assertEqual(len(found), 2)
        self.assertIn("private.invalid", found[0][1])
        self.assertIn("public.invalid", found[-1][1])

    def test_the_same_url_in_both_is_asked_once(self) -> None:
        with mock.patch.dict(os.environ, {CHANDLERY: "https://one.invalid",
                                          "SLIPWAI_INDEX": "https://one.invalid"}):
            self.assertEqual(len(channels()), 1)


class ReadTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        READ.clear()

    def tearDown(self) -> None:
        READ.clear()

    def read(self, *bases_: str) -> Index:
        with mock.patch.dict(os.environ, {CHANDLERY: ",".join(bases_), "SLIPWAI_INDEX": bases_[-1]}):
            return read_index()

    def test_every_channel_s_packages_are_in_one_listing(self) -> None:
        private = channel(self.area / "private", {"house": "1.0.0"})
        public = channel(self.area / "public", {"toy": "1.0.0"})
        found = self.read(private, public)
        self.assertEqual(sorted(r.name for r in matches(found, "")), ["house", "toy"])

    def test_the_earlier_channel_keeps_a_name_the_later_also_lists(self) -> None:
        """A channel that lists a name owns it, versions and all: merging the version lists would make one
        install fetch from whichever channel published most recently, which nobody chose."""
        private = channel(self.area / "private", {"toy": "1.0.0"})
        public = channel(self.area / "public", {"toy": "9.9.9"})
        found = self.read(private, public)
        rows = matches(found, "")
        self.assertEqual([(r.name, r.version) for r in rows], [("toy", "1.0.0")])

    def test_a_release_says_which_channel_listed_it(self) -> None:
        private = channel(self.area / "private", {"toy": "1.0.0"})
        said = "\n".join(show_lines(self.read(private), [], "toy"))
        self.assertIn("channel", said)

    def test_one_channel_being_down_does_not_empty_the_listing(self) -> None:
        public = channel(self.area / "public", {"toy": "1.0.0"})
        found = self.read((self.area / "nothing-here").as_uri(), public)
        self.assertEqual([r.name for r in matches(found, "")], ["toy"])
        self.assertTrue(found.unreachable)

    def test_and_the_listing_says_so_rather_than_looking_complete(self) -> None:
        from slipwai.cli_search import search_lines
        public = channel(self.area / "public", {"toy": "1.0.0"})
        said = search_lines(self.read((self.area / "nothing-here").as_uri(), public), [], "")
        self.assertTrue(any("could not be reached" in line for line in said), said)

    def test_every_channel_being_down_is_unreachable_and_not_an_empty_list(self) -> None:
        """"nothing available" and "could not ask" are different answers and a person acts on them differently."""
        with self.assertRaises(Unreachable):
            self.read((self.area / "nowhere").as_uri())


if __name__ == "__main__":
    unittest.main()
