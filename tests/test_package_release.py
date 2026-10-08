"""Building a release of either kind, and putting it in a channel.

The whole publisher path is one test at the end: `new`, then `register`, then the client reading what was
registered. Everything above it is the parts, because when that one fails it should be obvious which part
broke rather than that something did.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import package_new, package_release
from slipwai.errors import GenerationError
from slipwai.index_schema import CHANDLERY
from slipwai.language_index import READ, read_index

CORE = "9.0"


def packaged(area: Path, key: str = "lens", version: str = "0.1.0") -> Path:
    package_new.write("extension", key, area, CORE)
    (area / key / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    return area / key


class EntryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())

    def test_a_package_with_no_version_is_refused_with_the_command_that_writes_one(self) -> None:
        """The scaffold ships one; a package written before it did, or by hand, may not have."""
        package_new.write("extension", "lens", self.area, CORE)
        (self.area / "lens/VERSION").unlink()
        with self.assertRaises(GenerationError) as refused:
            package_release.release(self.area / "lens", self.area / "dist")
        self.assertIn("echo 0.1.0", str(refused.exception))

    def test_the_entry_is_read_off_the_package_and_never_typed(self) -> None:
        root = packaged(self.area)
        _, _, entry = package_release.release(root, self.area / "dist", publisher="ROBCOATVG")
        self.assertEqual(entry["kind"], "extension")
        self.assertEqual(entry["version"], "0.1.0")
        self.assertEqual(entry["publisher"], "ROBCOATVG")
        self.assertEqual(entry["extension"]["key"], "lens")

    def test_the_digest_is_of_the_file_that_was_built(self) -> None:
        import hashlib
        archive, _, entry = package_release.release(packaged(self.area), self.area / "dist")
        self.assertEqual(entry["sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())

    def test_a_language_package_releases_the_same_way(self) -> None:
        package_new.write("language", "rust", self.area, CORE)
        _, _, entry = package_release.release(self.area / "rust", self.area / "dist")
        self.assertEqual(entry["kind"], "language")
        self.assertIn("language", entry)

    def test_a_directory_that_is_no_package_says_so(self) -> None:
        (self.area / "nothing").mkdir()
        with self.assertRaises(GenerationError) as refused:
            package_release.kind_of(self.area / "nothing")
        self.assertIn("extension.json", str(refused.exception))


class ChannelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        self.channel = self.area / "channel"

    def test_one_file_per_entry_so_two_publishers_never_meet(self) -> None:
        package_release.register(packaged(self.area, "lens"), self.channel)
        package_release.register(packaged(self.area, "other"), self.channel)
        self.assertEqual(sorted(p.name for p in (self.channel / "entries").iterdir()),
                         ["lens-0.1.0.json", "other-0.1.0.json"])

    def test_the_index_is_rebuilt_from_them_rather_than_edited(self) -> None:
        package_release.register(packaged(self.area, "lens"), self.channel)
        package_release.register(packaged(self.area, "other"), self.channel)
        document = json.loads((self.channel / "slipwai-languages/index.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(document["packages"]), ["lens", "other"])
        self.assertEqual(document["index"], 2)

    def test_a_second_release_of_one_package_is_listed_beside_the_first(self) -> None:
        package_release.register(packaged(self.area / "one", "lens", "0.1.0"), self.channel)
        package_release.register(packaged(self.area / "two", "lens", "0.2.0"), self.channel)
        document = json.loads((self.channel / "slipwai-languages/index.json").read_text(encoding="utf-8"))
        self.assertEqual([e["version"] for e in document["packages"]["lens"]], ["0.1.0", "0.2.0"])

    def test_registering_the_same_bytes_again_is_not_a_problem_to_solve(self) -> None:
        root = packaged(self.area, "lens")
        package_release.register(root, self.channel)
        package_release.register(root, self.channel)
        self.assertEqual(len(list((self.channel / "entries").iterdir())), 1)

    def test_a_different_file_under_a_version_already_listed_is_refused(self) -> None:
        """A release is immutable once anybody has installed it: a replaced one makes a checked digest a lie."""
        root = packaged(self.area, "lens")
        package_release.register(root, self.channel)
        (root / "init.py").write_text("print('different')\n", encoding="utf-8")
        with self.assertRaises(GenerationError) as refused:
            package_release.register(root, self.channel)
        self.assertIn("release a new version", str(refused.exception))

    def test_an_entry_file_that_names_no_package_stops_the_rebuild_by_name(self) -> None:
        package_release.register(packaged(self.area, "lens"), self.channel)
        (self.channel / "entries/broken.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(GenerationError) as refused:
            package_release.rebuild(self.channel)
        self.assertIn("broken.json", str(refused.exception))

    def test_the_document_is_the_same_bytes_whatever_order_it_was_built_in(self) -> None:
        """It is checked rather than trusted, so it has to be a regeneration and not a resolution."""
        entries = [{"name": "b", "version": "2.0.0"}, {"name": "a", "version": "1.0.0"}]
        self.assertEqual(package_release.document(entries), package_release.document(entries[::-1]))


class WholePathTest(unittest.TestCase):
    """New, registered, then read by the client — which is the only test that proves the two halves agree."""

    def test_a_scaffolded_package_registers_and_is_found_by_the_client(self) -> None:
        area = Path(tempfile.mkdtemp())
        channel = area / "channel"
        package_release.register(packaged(area, "lens"), channel, publisher="ROBCOATVG")
        READ.clear()
        with mock.patch.dict(os.environ, {CHANDLERY: channel.as_uri(), "SLIPWAI_INDEX": channel.as_uri()}):
            found = read_index()
        READ.clear()
        release = found.releases["lens"][0]
        self.assertEqual((release.kind, release.version, release.publisher),
                         ("extension", "0.1.0", "ROBCOATVG"))
        self.assertTrue(release.url.endswith("lens-0.1.0.tar.gz"))


if __name__ == "__main__":
    unittest.main()


class ScaffoldShipsTest(unittest.TestCase):
    """What `new` writes has to carry the publisher through the other three verbs without a hand edit."""

    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())

    def test_an_extension_arrives_with_a_version_so_it_can_be_released_at_once(self) -> None:
        package_new.write("extension", "lens", self.area, CORE)
        _, _, entry = package_release.release(self.area / "lens", self.area / "dist")
        self.assertEqual(entry["version"], "0.1.0")

    def test_both_kinds_arrive_with_a_make_and_a_ci_that_calls_the_keel_s_workflow(self) -> None:
        for kind, key in (("extension", "lens"), ("language", "rust")):
            with self.subTest(kind=kind):
                package_new.write(kind, key, self.area, CORE)
                workflow = (self.area / key / ".github/workflows/verify.yml").read_text(encoding="utf-8")
                self.assertIn("/.github/workflows/package.yml", workflow)
                self.assertIn(f"kind: {kind}", workflow)
                self.assertIn("slipwai package register", (self.area / key / "Makefile").read_text("utf-8"))

    def test_the_scaffolded_makefile_names_no_path_from_the_machine_it_was_written_on(self) -> None:
        """It ships to a publisher, who has slipwai on PATH and not in this checkout."""
        package_new.write("extension", "lens", self.area, CORE)
        self.assertNotIn(str(Path.cwd()), (self.area / "lens/Makefile").read_text(encoding="utf-8"))
