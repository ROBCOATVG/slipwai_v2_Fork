"""Folding each fairway's own append-only files into the feature-level ones nobody edits.

Two fairways appending to one `decisions.md` is the shared-file problem from the other side: in the first
attempt it produced 54 renumbering commits in one night, and every merge of that file was a conflict in the
same three lines. So each fairway keeps its own and the feature-level file is rendered.

What is held here is the three properties that make that safe. The order is the instant each entry records,
so the folded file reads as one history rather than two lists stapled together. The ids are not touched, so
a citation written in a branch still resolves after the fold. And a rendered file that somebody edited is
refused, because a generated file edited by hand is a file that disagrees with its source and says nothing
about it.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "assets/toolkit/scripts/render-fairways.py"


def entry(id_: str, when: str, question: str) -> str:
    return (f"## {id_} — {question}\n"
            f"- **Stage:** plan · **Slice:** X · **When:** {when} · **Iteration:** 1\n"
            f"- **Decision:** something\n")


class Fixture(unittest.TestCase):
    """A project tree with two fairways. Both suites take it; neither runs the other's cases, because this
    one declares none of its own."""
    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts").mkdir()
        shutil.copy(SCRIPT, self.tree / "scripts/render-fairways.py")
        (self.tree / "project.json").write_text("{}", encoding="utf-8")
        (self.tree / "specs/ordering/slices").mkdir(parents=True)
        for fairway in ("ordering", "billing"):
            (self.tree / f"fairways/{fairway}").mkdir(parents=True)
        spec = importlib.util.spec_from_file_location("render", self.tree / "scripts/render-fairways.py")
        assert spec is not None and spec.loader is not None
        self.module = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(self.module)

    def write(self, fairway: str, body: str) -> None:
        (self.tree / f"fairways/{fairway}/decisions.md").write_text(body, encoding="utf-8")

    def folded(self) -> str:
        self.assertEqual(self.module.main([]), 0)
        return (self.tree / "specs/ordering/decisions.md").read_text(encoding="utf-8")


class FoldTest(Fixture):
    def test_two_fairways_each_deciding_once_both_appear(self) -> None:
        """Slice 5.10b's done-when."""
        self.write("ordering", entry("D-ORD-01", "2026-10-07T09:00:00Z", "which store"))
        self.write("billing", entry("D-BIL-01", "2026-10-07T10:00:00Z", "which gateway"))
        folded = self.folded()
        self.assertIn("D-ORD-01", folded)
        self.assertIn("D-BIL-01", folded)

    def test_the_order_is_the_instant_and_not_the_fairway(self) -> None:
        """Interleaving by time is what makes it one history rather than two lists stapled together."""
        self.write("ordering", entry("D-ORD-01", "2026-10-07T09:00:00Z", "first")
                   + entry("D-ORD-02", "2026-10-07T11:00:00Z", "third"))
        self.write("billing", entry("D-BIL-01", "2026-10-07T10:00:00Z", "second"))
        folded = self.folded()
        self.assertLess(folded.index("D-ORD-01"), folded.index("D-BIL-01"))
        self.assertLess(folded.index("D-BIL-01"), folded.index("D-ORD-02"))

    def test_no_id_is_changed_by_the_fold(self) -> None:
        """Which is the point of an id carrying its fairway: a gap in the numbers is not a gap."""
        self.write("ordering", entry("D-ORD-07", "2026-10-07T09:00:00Z", "which store"))
        self.write("billing", entry("D-BIL-02", "2026-10-07T08:00:00Z", "which gateway"))
        folded = self.folded()
        self.assertIn("## D-ORD-07 —", folded)
        self.assertIn("## D-BIL-02 —", folded)

    def test_an_entry_with_no_instant_sorts_after_the_ones_that_have_one(self) -> None:
        """Visible at the end rather than silently first, which is where an unsorted key would put it."""
        self.write("ordering", "## D-ORD-01 — undated\n- **Decision:** something\n")
        self.write("billing", entry("D-BIL-01", "2026-10-07T10:00:00Z", "dated"))
        folded = self.folded()
        self.assertLess(folded.index("D-BIL-01"), folded.index("D-ORD-01"))

    def test_the_rendered_file_says_it_is_rendered(self) -> None:
        self.write("ordering", entry("D-ORD-01", "2026-10-07T09:00:00Z", "which store"))
        self.assertIn("Never edit by hand", self.folded())


class CheckTest(Fixture):
    def test_a_file_that_matches_its_sources_passes(self) -> None:
        self.write("ordering", entry("D-ORD-01", "2026-10-07T09:00:00Z", "which store"))
        self.folded()
        self.assertEqual(self.module.main(["--check"]), 0)

    def test_a_rendered_file_edited_by_hand_is_refused(self) -> None:
        """A generated file somebody edited disagrees with its source and says nothing about it."""
        self.write("ordering", entry("D-ORD-01", "2026-10-07T09:00:00Z", "which store"))
        self.folded()
        path = self.tree / "specs/ordering/decisions.md"
        path.write_text(path.read_text(encoding="utf-8") + "\n## D-ORD-02 — snuck in\n", encoding="utf-8")
        self.assertEqual(self.module.main(["--check"]), 1)

    def test_a_fairway_deciding_after_the_last_fold_is_refused(self) -> None:
        self.write("ordering", entry("D-ORD-01", "2026-10-07T09:00:00Z", "which store"))
        self.folded()
        self.write("billing", entry("D-BIL-01", "2026-10-07T10:00:00Z", "which gateway"))
        self.assertEqual(self.module.main(["--check"]), 1)

    def test_a_project_with_no_fairway_files_is_not_a_failure(self) -> None:
        self.assertEqual(self.module.main(["--check"]), 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
