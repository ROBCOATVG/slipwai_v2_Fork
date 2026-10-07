"""The index document, in both the formats a published one may be written in.

Version 1 listed languages and nothing else. Version 2 lists packages, each declaring its kind, and carries
the four fields a person asked of version 1: who published it, a signature, a description and tags.

Both are read, because an index is a file on someone else's server: a keel that could only read the newer one
would make upgrading the keel break the index. Every fault in an entry drops that entry alone, for the same
reason — one bad line is not a reason the other forty do not install.
"""
from __future__ import annotations

import json
import unittest

import checkout_packages  # noqa: F401

from slipwai.index_schema import FORMATS, entry_of, format_of, releases_of

DOCUMENT = "https://example.invalid/slipwai-languages/index.json"
LANGUAGE = {"name": "toy", "core": ">=9.0,<10", "family": "toy",
            "backends": {"toy-plain": {"label": "Toy", "targets": ["none"], "options": {"http": ["none"]}}}}
EXTENSION = {"key": "lens", "name": "Lens", "description": "A code index", "kind": "extension",
             "core": ">=9.0,<10", "hooks": {"init": "init.py"}}


def entry(**extra: object) -> dict:
    return {"version": "1.0.0", "file": "toy-1.0.0.tar.gz", "sha256": "0" * 64, "language": LANGUAGE, **extra}


class FormatTest(unittest.TestCase):
    def test_both_formats_are_read(self) -> None:
        self.assertEqual(format_of({"index": 1, "languages": {}}), 1)
        self.assertEqual(format_of({"index": 2, "packages": {}}), 2)

    def test_a_format_this_keel_does_not_know_is_not_an_index(self) -> None:
        self.assertIsNone(format_of({"index": max(FORMATS) + 1, "packages": {}}))

    def test_a_document_whose_block_is_the_other_format_s_is_not_an_index(self) -> None:
        """A v2 header over a v1 body is a half-migrated index, and reading it as either would be a guess."""
        self.assertIsNone(format_of({"index": 2, "languages": {}}))

    def test_neither_an_object_nor_an_index_at_all(self) -> None:
        for data in ([], "index", {"packages": {}}, {"index": 2}):  # type: ignore[var-annotated]
            with self.subTest(data=data):
                self.assertIsNone(format_of(data))


class EntryTest(unittest.TestCase):
    def test_a_version_1_entry_is_a_language_without_saying_so(self) -> None:
        """Every package of version 1 is one, and the field arrived with extensions."""
        found = entry_of(DOCUMENT, "toy", entry())
        assert found is not None
        self.assertEqual((found.kind, found.name, found.version), ("language", "toy", "1.0.0"))

    def test_the_file_is_joined_against_the_document_so_a_relative_name_works(self) -> None:
        found = entry_of(DOCUMENT, "toy", entry())
        assert found is not None
        self.assertEqual(found.url, "https://example.invalid/slipwai-languages/toy-1.0.0.tar.gz")

    def test_an_extension_entry_carries_its_manifest_under_its_own_key(self) -> None:
        found = entry_of(DOCUMENT, "lens", {"version": "1.0.0", "file": "lens-1.0.0.tar.gz",
                                            "sha256": "0" * 64, "kind": "extension", "extension": EXTENSION})
        assert found is not None
        self.assertTrue(found.is_extension)
        self.assertEqual(found.fragment["key"], "lens")

    def test_the_kind_is_read_from_the_manifest_where_the_field_is_missing(self) -> None:
        """A hand-written entry that forgot `kind` works rather than vanishing."""
        found = entry_of(DOCUMENT, "lens", {"version": "1.0.0", "file": "lens-1.0.0.tar.gz",
                                            "sha256": "0" * 64, "extension": EXTENSION})
        assert found is not None
        self.assertTrue(found.is_extension)

    def test_an_entry_carrying_neither_manifest_is_dropped(self) -> None:
        self.assertIsNone(entry_of(DOCUMENT, "toy", {"version": "1.0.0", "file": "f", "sha256": "0" * 64}))

    def test_an_extension_whose_key_is_not_the_name_it_is_listed_under_is_dropped(self) -> None:
        """Otherwise the directory it installs into is not the name a person searched for."""
        self.assertIsNone(entry_of(DOCUMENT, "other", {"version": "1.0.0", "file": "f", "sha256": "0" * 64,
                                                       "kind": "extension", "extension": EXTENSION}))

    def test_a_digest_that_is_not_one_is_dropped(self) -> None:
        for digest in ("", "0" * 63, "z" * 64, "0" * 64 + "0", 64):
            with self.subTest(digest=digest):
                self.assertIsNone(entry_of(DOCUMENT, "toy", entry(sha256=digest)))

    def test_the_four_new_fields_are_carried(self) -> None:
        found = entry_of(DOCUMENT, "toy", entry(publisher="ROBCOATVG", signature="c2ln",
                                                description="A toy", tags=["toy", "testing"]))
        assert found is not None
        self.assertEqual((found.publisher, found.description), ("ROBCOATVG", "A toy"))
        self.assertEqual(found.tags, ("toy", "testing"))
        self.assertTrue(found.signed)

    def test_an_entry_with_no_signature_says_so_rather_than_claiming_one(self) -> None:
        found = entry_of(DOCUMENT, "toy", entry())
        assert found is not None
        self.assertFalse(found.signed)

    def test_a_field_longer_than_its_limit_is_dropped_and_the_entry_stays(self) -> None:
        """A megabyte of description is a document nobody should have read; it is not a broken package."""
        found = entry_of(DOCUMENT, "toy", entry(description="x" * 10_000, publisher="y" * 10_000))
        assert found is not None
        self.assertEqual((found.description, found.publisher), ("", ""))

    def test_tags_are_strings_short_and_few(self) -> None:
        found = entry_of(DOCUMENT, "toy", entry(tags=["fine", 7, "x" * 100, *[f"t{n}" for n in range(30)]]))
        assert found is not None
        self.assertEqual(found.tags[0], "fine")
        self.assertLessEqual(len(found.tags), 12)
        self.assertTrue(all(isinstance(tag, str) for tag in found.tags))

    def test_a_language_naming_something_that_is_not_a_name_is_dropped(self) -> None:
        """Nothing is printed or joined into a path before it has been held to the name rule."""
        bad = {**LANGUAGE, "family": "../../etc"}
        self.assertIsNone(entry_of(DOCUMENT, "toy", entry(language=bad)))


class ReleasesTest(unittest.TestCase):
    def test_one_bad_entry_does_not_take_the_rest_of_the_name_with_it(self) -> None:
        data = {"index": 1, "languages": {"toy": [entry(sha256="no"), entry(version="2.0.0")]}}
        found = releases_of(DOCUMENT, data, 1)
        self.assertEqual([r.version for r in found["toy"]], ["2.0.0"])

    def test_a_name_whose_entries_are_all_bad_is_not_listed_at_all(self) -> None:
        data = {"index": 1, "languages": {"toy": [entry(sha256="no")]}}
        self.assertEqual(releases_of(DOCUMENT, data, 1), {})

    def test_a_name_whose_entries_are_not_a_list_is_not_listed(self) -> None:
        self.assertEqual(releases_of(DOCUMENT, {"index": 2, "packages": {"toy": entry()}}, 2), {})

    def test_the_two_formats_differ_in_one_block_name_and_nothing_else(self) -> None:
        one = releases_of(DOCUMENT, {"index": 1, "languages": {"toy": [entry()]}}, 1)
        two = releases_of(DOCUMENT, {"index": 2, "packages": {"toy": [entry()]}}, 2)
        self.assertEqual(json.dumps(one, default=str), json.dumps(two, default=str))


if __name__ == "__main__":
    unittest.main()
