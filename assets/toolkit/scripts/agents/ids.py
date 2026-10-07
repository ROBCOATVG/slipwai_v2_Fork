#!/usr/bin/env python3
"""The next id for a fairway, counted out of its own deck log so two fairways can never mint the same one.

In the first attempt every berth took the next number after the last one it could see in its own checkout,
and every berth appended to one `decisions.md`. That cost 54 renumbering commits in a single night, and one
renumber rewrote 91 citations — every one of which had been correct when it was written. A claimed range of
numbers only shrinks the window; it does not close it.

So the id carries its fairway, and the counter is per fairway: `D-ORD-07`, `A-BIL-03`,
`ADR-ORD-2026-10-07-event-store`. Two fairways cannot collide because they are not counting the same thing.
Nothing is ever renumbered, which means a citation written today still resolves in a year.

**The count comes from the deck log, not from the file.** The file is rendered from the fairway's own
entries and a reader could be looking at a stale render, mid-merge, or at a feature-level aggregate that
holds two fairways' entries. The log is append-only, has one writer, and is the thing that recorded the
decision being counted.

**Version 1's ids stay valid.** A project that already has `D1` to `Dn` keeps them, resolving as they
always did, and only new ids carry a fairway. Renumbering the old ones to a new scheme would be the exact
cost this scheme exists to avoid, and `migrate` does not do it either.

    python3 scripts/agents/ids.py decision ORD      # D-ORD-07
    python3 scripts/agents/ids.py adversary BIL     # A-BIL-03
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[2]


ROOT = project_root(Path(__file__).resolve())
LOGS = ROOT / ".slipwai/logs"
V = 1
#: What each kind of record is counted and prefixed by. A kind not here has no id scheme and is refused
#: rather than given a guessed prefix, because an id is a citation and a wrong one resolves to nothing.
PREFIXES = {"decision": "D", "adversary": "A"}
#: The deck-log line kind that records each.
COUNTED = {"decision": "decision", "adversary": "stowed"}


def lines(feature: str, fairway: str) -> list[dict]:
    """Every line of one fairway's deck log, in the order written."""
    path = LOGS / feature / f"{fairway}.jsonl"
    if not path.is_file():
        return []
    found = []
    for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not text.strip():
            continue
        try:
            line = json.loads(text)
        except ValueError:
            raise SystemExit(f"ids: {path.name}:{number} is not JSON. Counting past a line nobody can read "
                             f"would mint an id somebody else already used.") from None
        if isinstance(line, dict) and line.get("v") != V:
            raise SystemExit(f"ids: {path.name}:{number} says v{line.get('v')} and this reader knows v{V}. "
                             f"Run `slipwai upgrade`.")
        if isinstance(line, dict):
            found.append(line)
    return found


def feature_in_flight() -> str:
    """The one feature with a log. A project between features has none, and the first id is 1."""
    found = sorted(path.name for path in LOGS.glob("*/") if path.is_dir()) if LOGS.is_dir() else []
    return found[0] if found else ""


def next_number(kind: str, fairway: str, feature: str = "") -> int:
    """How many of this kind this fairway has recorded, plus one."""
    if kind not in PREFIXES:
        raise SystemExit(f"ids: no id scheme for {kind!r}. There is one for: {', '.join(sorted(PREFIXES))}")
    counted = COUNTED[kind]
    written = lines(feature or feature_in_flight(), fairway)
    return sum(1 for line in written if line.get("kind") == counted) + 1


def next_id(kind: str, fairway: str, feature: str = "") -> str:
    """`D-ORD-07`. Two digits, so a fairway's ids sort as text for as long as it has fewer than a hundred."""
    number = next_number(kind, fairway, feature)
    return f"{PREFIXES[kind]}-{fairway}-{number:02d}"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[-2].strip(), file=sys.stderr)
        print("ids: give a kind and a fairway, as `ids.py decision ORD`", file=sys.stderr)
        return 1
    print(next_id(argv[0], argv[1], argv[2] if len(argv) > 2 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
