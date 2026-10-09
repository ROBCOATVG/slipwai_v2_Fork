"""6.1c: the keel ships an extension's parts to nobody, and names one nowhere a project reads.

The fault this holds closed is quiet. `scripts/agents/registry.json` is the keel's catalogue of coding
agents and it travels into every generated project, so a tool name written into one of its rows is handed
to a project that elected nothing — and a reader of that project, finding `mcp__codegraph__*` in the
allow-list its sessions run under, has every reason to think the keel brought the index. It did not; the
extension does, and only where somebody elected it.

Two halves, and the second is why this is a suite rather than a grep. The keel still *reads* a code index
if one is there — `slipwai survey` opens `.codegraph/codegraph.db` the way it reads `.git` — so the product
may be named where the keel is naming a file format or quoting dated evidence about one. What it may not do
is carry a live configuration value belonging to an extension. The test is on the live values.
"""
from __future__ import annotations

import json
import unittest

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT
from slipwai.catalog import CATALOG

REGISTRY = TOOLKIT_ROOT / "scripts/agents/registry.json"
#: Where a harness row carries something a session runs under, as opposed to a note about how it was read.
#: A `source`, a `how`, a `why` and a `projectMcpReason` are provenance: they record what was read on what
#: date, and rewriting one to drop a product's name would be falsifying the record rather than fixing it.
LIVE = ("permissions", "sandboxPermissions", "command", "headlessFlags", "worktreeFlags", "env", "modelFlag")
#: The keys the keel has ever shipped as an extension. Read from the catalogue where it has them, with the
#: three the plan names as the floor, so this keeps holding after one is renamed or another is added.
KEYS = tuple(sorted({*CATALOG.get("extensions", {}), "codegraph", "uipro", "ux-gates"}))


def values(node: object, keys: tuple[str, ...] = LIVE) -> list[tuple[str, str]]:
    """Every live configuration string in the registry, with the field it sits under."""
    found: list[tuple[str, str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in keys and isinstance(value, str):
                found.append((key, value))
            elif key in keys and isinstance(value, dict):
                found += [(key, str(one)) for one in value.values()]
            else:
                found += values(value, keys)
    elif isinstance(node, list):
        for one in node:
            found += values(one, keys)
    return found


class RegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_no_live_value_in_the_harness_registry_names_an_extension(self) -> None:
        """The one that was there: `--allowedTools '…,mcp__codegraph__*'` on Claude Code's headless row."""
        for field, value in values(self.document):
            for key in KEYS:
                with self.subTest(field=field, key=key):
                    self.assertNotIn(key, value.lower(), f"{field} carries {key}: it belongs to the extension")

    def test_a_row_that_can_take_an_extensions_tools_says_where_they_go(self) -> None:
        """`{tools}` is the whole mechanism, and a row without it is left exactly as recorded — so at least
        one row has to have it, or electing an extension would reach no harness at all."""
        placed = [value for _, value in values(self.document) if "{tools}" in value]
        self.assertTrue(placed, "no harness row has a {tools} placeholder for an elected extension")

    def test_the_placeholder_sits_inside_an_allow_list_rather_than_beside_it(self) -> None:
        """A second `--allowedTools` flag is not a merge on every harness that has one, so the names join
        the list already there."""
        for value in (one for _, one in values(self.document) if "{tools}" in one):
            with self.subTest(value=value):
                self.assertRegex(value, r"[A-Za-z][^'\"]*\{tools\}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
