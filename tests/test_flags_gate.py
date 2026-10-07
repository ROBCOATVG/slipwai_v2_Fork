"""The flag gate: declared and read, seeded off, asked through the reader, and struck when it is done.

`check-flags` was in every managed project's `verify` list and the script did not exist, so the gate it
names has never run anywhere. These are its five rules, each written as a tree that should be refused.

The fifth is the hygiene one and the only one that bites over time. Every flag system accumulates flags
nobody turns off; a flag on everywhere for longer than the window is a code path kept alive for nobody, a
branch every later change carries, and a test matrix twice the size it needs to be.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

import checkout_packages  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "assets/toolkit/scripts/check-flags.py"
NOW = datetime(2026, 10, 7, tzinfo=UTC)


class FlagGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts").mkdir()
        shutil.copy(GATE, self.tree / "scripts/check-flags.py")
        (self.tree / "project.json").write_text("{}", encoding="utf-8")
        (self.tree / "infra/service").mkdir(parents=True)
        (self.tree / "apps/orders/src").mkdir(parents=True)
        spec = importlib.util.spec_from_file_location("flags", self.tree / "scripts/check-flags.py")
        assert spec is not None and spec.loader is not None
        self.gate = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(self.gate)

    def declare(self, body: str) -> None:
        (self.tree / "infra/service/flags.auto.tfvars").write_text(body, encoding="utf-8")

    def code(self, body: str, name: str = "place.ts") -> None:
        (self.tree / f"apps/orders/src/{name}").write_text(body, encoding="utf-8")

    def test_a_flag_declared_and_read_and_seeded_off_passes(self) -> None:
        self.declare('place_order = "off"\n')
        self.code('if (flag("place_order")) { ship(); }\n')
        self.assertEqual(self.gate.faults(NOW), [])

    def test_a_flag_nobody_reads_is_refused(self) -> None:
        """A switch wired to nothing does nothing when flipped, and nobody finds out until they flip it."""
        self.declare('place_order = "off"\n')
        self.code("// nothing asks for it\n")
        self.assertIn("declared and no code asks for it", " ".join(self.gate.faults(NOW)))

    def test_a_key_read_and_declared_nowhere_is_refused(self) -> None:
        """It reads off for ever: the capability is dark and there is nothing to flip."""
        self.declare('place_order = "off"\n')
        self.code('if (flag("place_order") && flag("bulk_upload")) { ship(); }\n')
        self.assertIn("declared nowhere, so it reads off for ever", " ".join(self.gate.faults(NOW)))

    def test_a_new_flag_seeded_on_is_refused(self) -> None:
        """A release that happened at merge time, which is what a flag exists to prevent."""
        self.declare('place_order = "on"\n')
        self.code('if (flag("place_order")) { ship(); }\n')
        self.assertIn("is a release that happened at merge time", " ".join(self.gate.faults(NOW)))

    def test_a_read_that_goes_round_the_reader_is_refused(self) -> None:
        """Naming the variable loses the single spelling, the transform and the seam a test drives."""
        self.declare('place_order = "off"\n')
        self.code('if (process.env.FLAG_PLACE_ORDER) { ship(); }\nflag("place_order");\n')
        self.assertIn("Ask the reader by key", " ".join(self.gate.faults(NOW)))

    def test_the_reader_itself_may_name_the_variable(self) -> None:
        """It is the one place that derives the variable from the key."""
        self.declare('place_order = "off"\n')
        self.code('if (flag("place_order")) { ship(); }\n')
        self.code("const name = `FLAG_${key.toUpperCase()}`;\n", name="flags.ts")
        self.assertEqual(self.gate.faults(NOW), [])

    def test_a_flag_on_everywhere_inside_the_window_passes(self) -> None:
        self.declare('place_order = "on" # hoisted: 2026-10-01\n')
        self.code('if (flag("place_order")) { ship(); }\n')
        self.assertEqual(self.gate.faults(NOW), [])

    def test_a_flag_on_everywhere_past_the_window_is_refused(self) -> None:
        """A flag nobody will turn off is a code path kept alive for nobody."""
        self.declare('place_order = "on" # hoisted: 2026-01-01\n')
        self.code('if (flag("place_order")) { ship(); }\n')
        self.assertIn("over the 30-day window", " ".join(self.gate.faults(NOW)))

    def test_an_operations_flag_is_never_overdue(self) -> None:
        """A kill switch is meant to live for ever; only a flag a slice opened is on a clock."""
        self.declare('read_only = "on" # hoisted: 2024-01-01 kind: operations\n')
        self.code('if (flag("read_only")) { ship(); }\n')
        self.assertEqual(self.gate.faults(NOW), [])

    def test_a_project_with_no_flag_file_is_not_a_failure(self) -> None:
        self.assertEqual(self.gate.faults(NOW), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
