"""`GLOSSARY.md` says what the plan says, proven rather than remembered.

A word that means one thing in the plan and another at the root of the repository is worse than no
glossary: a session reads whichever it finds first and never learns there was a second. So the root file
is written from the plan by `scripts/glossary.py`, and this holds the committed copy to it.

When this fails, the fix is `python3 scripts/glossary.py` and a commit of both files.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import re
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY / "scripts/glossary.py"

_spec = importlib.util.spec_from_file_location("glossary_script", SCRIPT)
assert _spec is not None and _spec.loader is not None
glossary = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(glossary)


class GlossaryTest(unittest.TestCase):
    def test_the_committed_glossary_is_what_the_plan_would_write(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = glossary.main(["--check"])
        self.assertEqual(code, 0, out.getvalue())

    def test_every_word_the_plan_defines_reaches_the_glossary(self) -> None:
        """The table is copied whole; this catches a copy that silently stopped halfway."""
        plan = glossary.PLAN.read_text(encoding="utf-8")
        words = [row.split("|")[1].strip() for row in glossary.vocabulary(plan) if row.startswith("| **")]
        self.assertGreater(len(words), 20, "the vocabulary should not have shrunk to nothing")
        page = glossary.GLOSSARY.read_text(encoding="utf-8")
        for word in words:
            self.assertIn(word, page)

    def test_no_meaning_is_written_in_version_1s_words(self) -> None:
        """The plan's own rule: nothing in version 2 is called a workstation, a workstream, a lane or a
        runner. Those words belong in the third column, which says what version 1 called the thing, and
        nowhere in the second, which says what the thing is now."""
        # Whole words: "swimlanes" on the fleet board is dataviz's word for a row, not version 1's
        # word for a berth, and a substring match would refuse it.
        retired = ("workstation", "workstreams?", "lanes?", "runners?")
        for line in glossary.GLOSSARY.read_text(encoding="utf-8").splitlines():
            if not line.startswith("| **"):
                continue
            word, meaning = (part.strip() for part in line.split("|")[1:3])
            for name in retired:
                with self.subTest(word=word, retired=name):
                    found = re.search(rf"\b{name}\b", meaning.lower())
                    self.assertIsNone(found, f"{word}'s meaning uses the retired name {name!r}")

    def test_a_drifted_glossary_is_refused(self) -> None:
        """The gate has to fail when the two disagree, or it is decoration."""
        page = glossary.glossary(glossary.PLAN.read_text(encoding="utf-8"))
        self.assertNotEqual(page, page.replace("| **Keel**", "| **Core**", 1))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
