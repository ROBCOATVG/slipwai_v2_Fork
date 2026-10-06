#!/usr/bin/env python3
"""Write `GLOSSARY.md` from the plan's vocabulary, so the two cannot drift.

Every name in slipwai comes from the slipway and the harbour, and a name that means one thing in the plan
and another at the root of the repository is worse than no glossary at all: a session reads whichever it
finds first. So there is one source — section 1 of the plan — and this script copies it to the root, where
a session, the `wtf` skill and a reader who never opens `docs/` all find it.

`--check` compares the committed file against what this script would write and fails if they differ, which
is what `tests/test_glossary.py` runs. Edit the plan, run `python3 scripts/glossary.py`, commit both.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/slipwai-2-plan.md"
GLOSSARY = ROOT / "GLOSSARY.md"
SECTION = "## 1. The words this plan uses"

HEADER = """<!-- Written by scripts/glossary.py from the vocabulary table in section 1 of
     docs/slipwai-2-plan.md. Do not edit by hand: edit the plan, run `python3 scripts/glossary.py`,
     and commit both. -->

# The words slipwai uses

Every name in slipwai comes from the slipway and the harbour. Read this first. Everything else in the
repository uses these words without explaining them again.

Nothing in version 2 is called a workstation, a workstream, a lane or a runner. Where something here names
a version 1 idea, it uses version 1's own name for it and says so.
"""


def vocabulary(page: str) -> list[str]:
    """The lines of the vocabulary table in section 1: its header, its rule, and every row."""
    lines = page.splitlines()
    if SECTION not in lines:
        raise SystemExit(f"glossary: {PLAN.name} has no section headed {SECTION!r}")
    start = lines.index(SECTION) + 1
    table: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.startswith("|"):
            table.append(line)
        elif table:
            # The table has ended and the section has gone on to prose; the glossary wants the table.
            break
    if not table:
        raise SystemExit(f"glossary: no vocabulary table under {SECTION!r} in {PLAN.name}")
    return table


def glossary(page: str) -> str:
    """The glossary page: the plan's vocabulary table under an introduction of its own."""
    return HEADER + "\n" + "\n".join(vocabulary(page)) + "\n"


def main(arguments: list[str]) -> int:
    wanted = glossary(PLAN.read_text(encoding="utf-8"))
    if "--check" not in arguments:
        GLOSSARY.write_text(wanted, encoding="utf-8")
        print(f"glossary: wrote {GLOSSARY.name} from {PLAN.relative_to(ROOT)}")
        return 0
    found = GLOSSARY.read_text(encoding="utf-8") if GLOSSARY.is_file() else ""
    if found == wanted:
        print(f"glossary: {GLOSSARY.name} is in step with {PLAN.relative_to(ROOT)}")
        return 0
    print(
        f"glossary: {GLOSSARY.name} is out of step with section 1 of {PLAN.relative_to(ROOT)}.\n"
        "  Run: python3 scripts/glossary.py",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
