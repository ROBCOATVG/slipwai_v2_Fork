#!/usr/bin/env python3
"""What can be brought back next, and what each remaining module is still waiting on.

Version 2 is version 1 taken apart and reassembled, one module at a time, and the plan was written
forwards from the design while the dependencies run backwards from the code. Six slices in phase 2 turned
out to be unbuildable where they were written — `catalog.py` sits near the top of the import graph, not
the bottom; `loaded.py` reads the catalogue it was slated to arrive with; the conformance suite generates
a project and so needs the whole scaffold. Each was found by attempting it.

This finds them on paper instead. `docs/bring-back.tsv` records every module the experiment has, what it
imports, and which asset trees it reads; this reads that against what the keel has now and says which
modules are ready, which are blocked and by what.

    python3 scripts/bring-back.py              what is ready now, and the waves after it
    python3 scripts/bring-back.py --waiting     every module not back yet, and what each waits on
    python3 scripts/bring-back.py --check       fail when the keel holds a module the ledger does not

`--check` runs in the gate. It does not check the order — a person may bring a module back early and
teach the ledger why — only that nothing in `src/slipwai/` is missing from the ledger, so the next
reading of it is complete.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEEL = ROOT / "src/slipwai"
LEDGER = ROOT / "docs/bring-back.tsv"
# The asset trees the keel already has. A module that reads one it has not got is blocked on the tree,
# which the import graph does not show and which cost phase 2 two corrections on its own.
ASSETS_HERE = {"BACKING_SERVICE_ROOT", "PRUNER", "TARGET_ROOT"}
# Written for version 2 rather than brought back, so the ledger will never hold them.
OWN = {"family_only", "catalog_checks"}
# Present, but in a version 2 shape that is not the experiment's yet: `cli` answers `--version` and will
# grow a verb per slice, `assets` holds the paths and not the asset trees, `__init__` and `__main__` are
# the package's own. The ledger's row for each describes what it becomes, not what is here, so they are
# left out of the check that everything back has what it imports.
PARTIAL = {"cli", "assets", "__init__", "__main__"}


@dataclass(frozen=True)
class Module:
    """One row of the ledger: how big it is, what it imports, and which asset trees it reads."""

    lines: int
    needs: frozenset[str]
    assets: frozenset[str]


def ledger() -> dict[str, Module]:
    """Every module the experiment has, by name, with what it needs."""
    rows: dict[str, Module] = {}
    with LEDGER.open(encoding="utf-8") as handle:
        for row in csv.DictReader((line for line in handle if not line.startswith("#")), delimiter="\t"):
            rows[row["module"]] = Module(int(row["lines"]), frozenset(row["needs"].split()),
                                         frozenset(row["assets"].split()))
    return rows


def here() -> set[str]:
    """Every module the keel has now, by the name the ledger calls it."""
    found = set()
    for path in KEEL.rglob("*.py"):
        parts = [p for p in path.relative_to(KEEL).with_suffix("").parts if p != "__init__"]
        found.add(".".join(parts) if parts else "__init__")
    return found


def satisfied(need: str, done: set[str]) -> bool:
    """A need is met by the module itself, or by the package it names: `project.flags` satisfies `project`."""
    return need in done or need.split(".")[0] in done or any(d.startswith(f"{need}.") for d in done)


def waves(rows: dict[str, Module], done: set[str]) -> list[tuple[list[str], set[str]]]:
    """The remaining modules in the order they can be built, and the asset trees each wave first needs."""
    left = {m for m in rows if m not in done}
    assets, out = set(ASSETS_HERE), []
    while left:
        ready = sorted(m for m in left
                       if all(satisfied(n, done) for n in rows[m].needs) and rows[m].assets <= assets)
        wanted: set[str] = set()
        if not ready:
            ready = sorted(m for m in left if all(satisfied(n, done) for n in rows[m].needs))
            if not ready:
                out.append((sorted(left), {"a cycle or a module the ledger does not hold"}))
                break
            wanted = {a for m in ready for a in rows[m].assets} - assets
            assets |= wanted
        out.append((ready, wanted))
        done |= set(ready)
        left -= set(ready)
    return out


def main(arguments: list[str]) -> int:
    rows, done = ledger(), here()
    if "--check" in arguments:
        unknown = sorted(done - set(rows) - OWN)
        if unknown:
            print("bring-back: the keel holds modules the ledger does not know:\n", file=sys.stderr)
            for name in unknown:
                print(f"  {name}", file=sys.stderr)
            print(f"\n  Run: python3 {Path(__file__).relative_to(ROOT)} --read", file=sys.stderr)
            return 1
        print(f"bring-back: {len(done - set(rows) - OWN)} unknown; {len(done & set(rows))} of {len(rows)} back")
        return 0

    plan = waves(rows, set(done))
    if "--waiting" in arguments:
        for name in sorted(set(rows) - done):
            missing = sorted(n for n in rows[name].needs if not satisfied(n, done))
            trees = sorted(rows[name].assets - ASSETS_HERE)
            print(f"{name:<34} {', '.join(missing) or '—':<46} {', '.join(trees)}")
        return 0

    back = len(done & set(rows))
    print(f"{back} of {len(rows)} modules back. {len(plan)} waves left.\n")
    for number, (ready, wanted) in enumerate(plan, start=1):
        if wanted:
            print(f"  ── first needs the asset trees: {', '.join(sorted(wanted))}")
        total = sum(rows[m].lines for m in ready if m in rows)
        print(f"  wave {number}: {len(ready)} modules, {total} lines")
        if number <= 2:
            print(f"      {', '.join(ready)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
