"""An `extension.json`, and the six obligations its entry point meets.

An extension is a package like a language is. The difference is narrow: a language is asked at generate
time to write the skeleton; an extension is elected at `./init`, after the skeleton exists, and never
changes generated code. Everything else is the same, which is why the manifests differ only in what they
declare.

The six obligations are each a failure somebody had, and the suite names them rather than describing them.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai import extension_shape as shape
from slipwai import extension_tools as tools

WHOLE = {"key": "codegraph", "name": "CodeGraph", "description": "A code index for agents",
         "kind": "extension", "core": ">=9.0,<10"}


class ValidationTest(unittest.TestCase):
    def test_a_whole_manifest_passes(self) -> None:
        shape.validate(WHOLE)

    def test_every_required_field_is_required_by_name(self) -> None:
        for field in shape.REQUIRED:
            with self.subTest(field=field):
                short = {key: value for key, value in WHOLE.items() if key != field}
                with self.assertRaises(ValueError) as refused:
                    shape.validate(short)
                self.assertIn(field, str(refused.exception))

    def test_the_wrong_kind_says_which_manifest_a_language_uses(self) -> None:
        """The loader reads the two apart, so the refusal should say which one this should have been."""
        with self.assertRaises(ValueError) as refused:
            shape.validate({**WHOLE, "kind": "language"})
        self.assertIn("language.json", str(refused.exception))

    def test_a_field_the_keel_does_not_read_is_refused_with_the_list(self) -> None:
        """Otherwise it is silently ignored, which reads exactly like being honoured."""
        with self.assertRaises(ValueError) as refused:
            shape.validate({**WHOLE, "colour": "blue"})
        self.assertIn("colour", str(refused.exception))
        self.assertIn("It may declare:", str(refused.exception))

    def test_ignore_is_gitignore_text_and_tags_are_strings(self) -> None:
        shape.validate({**WHOLE, "ignore": ".codegraph/\n", "tags": ["index", "agents"]})
        for bad in ({"ignore": [".codegraph/"]}, {"tags": "index"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                shape.validate({**WHOLE, **bad})

    def test_a_hook_on_a_point_the_keel_does_not_fire_is_refused_here_too(self) -> None:
        """Checked on the publisher's machine, where they can fix it, rather than at somebody's `./init`."""
        with self.assertRaises(KeyError):
            shape.validate({**WHOLE, "hooks": {"whenever": "x.py"}})

    def test_a_declared_hook_passes(self) -> None:
        shape.validate({**WHOLE, "hooks": {"check": "hooks/check.py"}})


class CatalogueTest(unittest.TestCase):
    def test_only_the_three_fields_the_menu_has_ever_used_are_merged(self) -> None:
        """Merging the whole manifest would make a menu that renders whatever the newest one added."""
        entry = shape.catalogue_entry({**WHOLE, "publisher": "ROBCOATVG", "tags": ["x"],
                                       "hooks": {"check": "c.py"}, "ignore": ".codegraph/\n"})
        self.assertEqual(set(entry), {"name", "description", "ignore"})

    def test_an_extension_leaving_no_state_carries_no_ignore(self) -> None:
        self.assertEqual(set(shape.catalogue_entry(WHOLE)), {"name", "description"})


class ObligationTest(unittest.TestCase):
    def test_there_are_six_and_each_says_what_it_holds(self) -> None:
        self.assertEqual(len(shape.OBLIGATIONS), 6)
        for name, why in shape.OBLIGATIONS:
            with self.subTest(obligation=name):
                self.assertTrue(name and why)

    def test_the_names_are_what_conformance_reports(self) -> None:
        self.assertEqual(shape.obligations(),
                         ("idempotent", "non-fatal", "projects", "gated", "recovers", "merges"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


class KeyTest(unittest.TestCase):
    """`key` is what a person types and what the directory is called; `name` is the product's own."""

    def test_a_key_that_is_not_a_slug_is_refused_saying_what_it_becomes(self) -> None:
        with self.assertRaises(ValueError) as refused:
            shape.validate({**WHOLE, "key": "UI/UX Pro Max"})
        said = str(refused.exception)
        self.assertIn("--extension", said)
        self.assertIn("`name`", said)

    def test_the_name_is_free_to_be_a_product_name(self) -> None:
        shape.validate({**WHOLE, "key": "uipro", "name": "UI/UX Pro Max"})

    def test_the_catalogue_entry_carries_the_name_not_the_key(self) -> None:
        entry = shape.catalogue_entry({**WHOLE, "key": "uipro", "name": "UI/UX Pro Max"})
        self.assertEqual(entry["name"], "UI/UX Pro Max")
        self.assertNotIn("key", entry)


class ToolsTest(unittest.TestCase):
    """`tools`: the names an extension needs a headless session allowed to call.

    6.1c's half of the manifest. The keel's harness registry carried `mcp__codegraph__*` in Claude Code's
    allow-list, so every generated project was handed one extension's tool name whether it had elected that
    extension or not — and a project that elected none still shipped a file naming one. The fact belongs to
    whoever brings the tool, and this is where they declare it.
    """

    def test_an_extension_may_declare_none(self) -> None:
        shape.validate(WHOLE)
        self.assertEqual(tools.declared(WHOLE), ())

    def test_a_declared_list_is_read_in_the_order_it_was_written(self) -> None:
        """Order is the extension's: a broad pattern written after a narrow one meant something by it."""
        manifest = {**WHOLE, "tools": ["mcp__pro__*", "Bash(pro:*)"]}
        shape.validate(manifest)
        self.assertEqual(tools.declared(manifest), ("mcp__pro__*", "Bash(pro:*)"))

    def test_a_tool_that_is_not_a_string_is_refused_by_what_the_field_is(self) -> None:
        with self.assertRaises(ValueError) as refused:
            shape.validate({**WHOLE, "tools": ["fine", 7]})
        self.assertIn("list of tool names", str(refused.exception))

    def test_an_empty_name_is_refused_rather_than_allowed_as_nothing(self) -> None:
        """An empty pattern in an allow-list is a flag with a stray comma in it, which a harness reads as
        its own business and this keel would never hear about again."""
        with self.assertRaises(ValueError):
            shape.validate({**WHOLE, "tools": ["  "]})

    def test_tools_is_a_field_the_keel_reads_rather_than_an_unknown_one(self) -> None:
        self.assertIn("tools", shape.OPTIONAL)
