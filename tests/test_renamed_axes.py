"""An axis this keel has renamed, read under the name whatever is on disk uses.

`axes.RENAMED` is one table with three readers, and this is the suite that holds all three to it: a
`language.json` a package shipped before the rename (`language_directory.under_current_names`), a
`project.json` a project was generated with before it (`manifest.reading`), and `docs/rename.json`, which
is the same row again for the files `migrate` rewrites. The keel is the one that renamed the axis, so
nothing on disk is refused for still spelling it the old way.

Only the axis moves. An option is still `postgres`, a capability is still `event-store-postgres`, and a
fragment or a manifest naming no renamed axis comes back exactly as it was written — which is the half
that stops a rename table quietly rewriting things nobody renamed.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from test_language_directory import CORE, FRAGMENT, write_package

from slipwai.assets import ROOT
from slipwai.axes import RENAMED, named_axes
from slipwai.language_directory import read
from slipwai.manifest import MANIFEST_SCHEMA, apps_from_manifest
from slipwai.selection import Selection

RENAMES = json.loads((ROOT / "docs/rename.json").read_text(encoding="utf-8"))


def manifest(selection: dict) -> dict:
    """The smallest manifest with one service in it, answering `selection`.

    Written by hand rather than generated: the rename has to be readable on a keel with no package of
    that language loaded at all, which is what a `replay` on somebody else's machine often is.
    """
    return {
        "schema": MANIFEST_SCHEMA,
        "deployables": {
            "service": {
                "kind": "service", "path": "apps/service", "language": "toy", "framework": "plain",
                "port": 3000, "selection": selection,
            },
        },
    }


class TableTest(unittest.TestCase):
    def test_the_rename_table_says_what_the_keel_reads(self) -> None:
        """Two copies of one fact: `axes.RENAMED` is what a keel reads back, `docs/rename.json` is what
        `migrate` rewrites, and a row in one and not the other is a project half-renamed."""
        fields = {row["from"]: row["to"] for row in RENAMES["renames"] if row["kind"] == "field"}
        for old, new in RENAMED.items():
            with self.subTest(axis=old):
                self.assertEqual(fields.get(old), new, "the rename table has no row for this axis")

    def test_only_the_axis_moves(self) -> None:
        self.assertEqual(named_axes({"event-store": "postgres"}), {"persistence": "postgres"})
        self.assertEqual(named_axes({"auth": "keycloak"}), {"auth": "keycloak"})


class FragmentTest(unittest.TestCase):
    """A package built before the rename stays on the menu rather than dropping off it."""

    def read_one(self, fragment: dict) -> dict:
        with tempfile.TemporaryDirectory() as parent:
            write_package(Path(parent), fragment=fragment)
            packages, refusals = read(Path(parent), CORE)
            self.assertEqual(refusals, [])
            return packages[0].fragment

    def test_a_backend_answering_the_old_name_answers_the_new_one(self) -> None:
        written = {**FRAGMENT, "backends": {"bad": {
            "label": "Bad", "targets": ["none"],
            "options": {"event-store": ["memory", "postgres"], "http": ["none"]},
            "defaults": {"event-store": "postgres"},
        }}}
        row = self.read_one(written)["backends"]["bad"]
        self.assertEqual(
            row["options"],
            {"persistence": ["memory", "postgres"], "http": ["none"], "write-model": ["events"]},
        )
        self.assertEqual(row["defaults"], {"persistence": "postgres"})

    def test_a_backend_from_before_the_rung_was_an_axis_is_read_onto_the_rung_it_was_built_for(self) -> None:
        """The rename alone would have changed the answer, not just its spelling.

        `write-model` has `state` as its `absent`, and an axis no loaded backend answers falls to its
        absent. So a package that knew only `event-store` would generate state-stored services while
        shipping nothing but event-store adapters — and the rung is the one answer the keel says cannot be
        walked back once a service holds data.
        """
        written = {**FRAGMENT, "backends": {"bad": {
            "label": "Bad", "targets": ["none"],
            "options": {"event-store": ["postgres"], "http": ["none"]},
        }}}
        self.assertEqual(self.read_one(written)["backends"]["bad"]["options"]["write-model"], ["events"])

    def test_a_backend_that_already_answers_the_rung_keeps_both_of_its_answers(self) -> None:
        """Only a package old enough to spell `event-store` is read forward; one rebuilt on the protocol
        that has the rung declares both rows itself, and nothing here narrows it to one."""
        written = {**FRAGMENT, "backends": {"bad": {
            "label": "Bad", "targets": ["none"],
            "options": {"event-store": ["postgres"], "write-model": ["events", "state"], "http": ["none"]},
        }}}
        self.assertEqual(
            self.read_one(written)["backends"]["bad"]["options"]["write-model"], ["events", "state"]
        )

    def test_an_option_the_package_declares_under_the_old_name_moves_too(self) -> None:
        written = {**FRAGMENT, "axes": {"event-store": {"duck": {"label": "Duck"}}}}
        self.assertEqual(self.read_one(written)["axes"], {"persistence": {"duck": {"label": "Duck"}}})

    def test_a_fragment_naming_no_renamed_axis_is_left_exactly_as_written(self) -> None:
        self.assertEqual(self.read_one(dict(FRAGMENT)), FRAGMENT)


class ManifestTest(unittest.TestCase):
    """A project generated before the rename replays without being migrated first."""

    def test_a_selection_recorded_under_the_old_name_reads_back_under_the_new_one(self) -> None:
        read = apps_from_manifest(manifest({"event-store": "postgres", "http": "toy-serve"}))
        self.assertEqual(read[0].selection, Selection({"persistence": "postgres", "http": "toy-serve"}))

    def test_a_selection_naming_no_renamed_axis_is_read_exactly_as_written(self) -> None:
        read = apps_from_manifest(manifest({"http": "toy-serve"}))
        self.assertEqual(read[0].selection, Selection({"http": "toy-serve"}))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
