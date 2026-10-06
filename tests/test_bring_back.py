"""The ledger of what is left to bring back, and whether it still describes this keel.

Six slices in phase 2 were unbuildable where the plan wrote them, each found by attempting it. The ledger
is how the rest are found on paper: `docs/bring-back.tsv` records what every module of the experiment
imports and which asset trees it reads, and `scripts/bring-back.py` reads it against what the keel has.

What is held here is that the ledger stays true. A module in the keel that the ledger does not know means
the next reading of it is wrong, and a reading that is wrong is worse than none — it would say a slice is
ready when it is not, which is the mistake the ledger exists to stop making.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY / "scripts/bring-back.py"

_spec = importlib.util.spec_from_file_location("bring_back", SCRIPT)
assert _spec is not None and _spec.loader is not None
bring_back = importlib.util.module_from_spec(_spec)
# Registered before it runs: `@dataclass` resolves its annotations through `sys.modules[__module__]`,
# and a module loaded from a path that is not registered there fails with an AttributeError on None.
sys.modules[_spec.name] = bring_back
_spec.loader.exec_module(bring_back)


class LedgerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = bring_back.ledger()
        self.here = bring_back.here()

    def test_the_ledger_knows_every_module_the_keel_has(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = bring_back.main(["--check"])
        self.assertEqual(code, 0, out.getvalue())

    def test_the_ledger_is_not_empty_and_is_bigger_than_the_keel(self) -> None:
        """It is the whole of version 1; the keel is what has come back so far."""
        self.assertGreater(len(self.rows), 100)
        self.assertLess(len(self.here), len(self.rows))

    def test_every_module_the_keel_has_is_either_in_the_ledger_or_version_2s_own(self) -> None:
        self.assertEqual(self.here - set(self.rows) - bring_back.OWN, set())

    def test_nothing_brought_back_whole_is_still_waiting_on_something(self) -> None:
        """A module that is back while something it imports is not would not import at all, so this is
        really a statement about the ledger: its `needs` are the real ones.

        The partial ones are left out by name. `cli` is version 2's own, answering `--version` and
        growing a verb per slice; the ledger's row for it lists every verb the experiment ended with.
        """
        for name in sorted(self.here & set(self.rows) - bring_back.PARTIAL):
            for need in self.rows[name].needs:
                with self.subTest(module=name, needs=need):
                    self.assertTrue(bring_back.satisfied(need, self.here))

    def test_the_waves_cover_everything_left_exactly_once(self) -> None:
        seen = [m for ready, _ in bring_back.waves(self.rows, set(self.here)) for m in ready]
        self.assertEqual(sorted(seen), sorted(set(self.rows) - self.here))
        self.assertEqual(len(seen), len(set(seen)))

    def test_a_module_is_never_in_a_wave_before_something_it_needs(self) -> None:
        """The one property the ordering is for."""
        done = set(self.here)
        for ready, _ in bring_back.waves(self.rows, set(self.here)):
            for name in ready:
                for need in self.rows[name].needs:
                    with self.subTest(module=name, needs=need):
                        self.assertTrue(bring_back.satisfied(need, done | set(ready)))
            done |= set(ready)

    def test_a_partial_module_is_one_the_keel_actually_has(self) -> None:
        """The list is an exemption, so it must not quietly name something absent and exempt nothing."""
        self.assertEqual(bring_back.PARTIAL - self.here, set())

    def test_a_module_inside_a_package_satisfies_a_need_for_the_package(self) -> None:
        self.assertTrue(bring_back.satisfied("project", {"project.flags"}))
        self.assertTrue(bring_back.satisfied("project.flags", {"project.flags"}))
        self.assertFalse(bring_back.satisfied("project.flags", {"catalog"}))

    def test_a_package_does_not_satisfy_a_need_for_a_module_inside_it(self) -> None:
        """The rule runs one way. `project/__init__.py` is six lines and knows nothing, and the first
        version of this called `project.agents` ready on the strength of it."""
        self.assertFalse(bring_back.satisfied("project.stage_models", {"project"}))
        self.assertFalse(bring_back.satisfied("project.stage_models", {"project", "project.flags"}))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
