#!/usr/bin/env python3
"""Fold each fairway's append-only files into the feature-level ones nobody edits by hand.

Two fairways appending to one `decisions.md` is the shared-file problem the ids already fixed from the other
side: in the first attempt it produced 54 renumbering commits in a night, and every merge of that file was a
conflict in the same three lines. So each fairway writes its own — `fairways/<name>/decisions.md`,
`adversary-log.md` — and two fairways never meet on one line, because they are never in one file.

The feature-level file still has to exist, because a reader wants one list and a citation has to resolve. It
is **rendered**, by this, and never written: the sources are the fairway files, the order is the instant each
entry records, and `--check` refuses a rendered file that is not what its sources render to. That is
`scripts/glossary.py --check`'s pattern, which this repository has used since slice 1.6 for the same reason —
a generated file somebody edited is a file that disagrees with its source and says nothing about it.

**The order is the instant, not the fairway.** Interleaving by time is what makes the feature-level file read
as one history rather than as two lists stapled together. Ids are *not* renumbered to match, and that is the
point of them carrying their fairway: `D-ORD-07` sitting between `D-BIL-02` and `D-BIL-03` is not a gap, and
a reader who knows the scheme is not confused by it.

    python3 scripts/render-fairways.py           # write the feature-level files
    python3 scripts/render-fairways.py --check    # fail where one is not what its sources render to
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[1]


ROOT = project_root(Path(__file__).resolve())
FAIRWAYS = ROOT / "fairways"
SPECS = ROOT / "specs"
#: The append-only files a fairway keeps its own copy of, and the feature-level file each folds into.
FOLDED = ("decisions.md", "adversary-log.md")
#: The instant an entry records, which is what the fold orders by. An entry without one sorts after the
#: entries that have one, in the order its own file had it — visible rather than silently first.
WHEN = re.compile(r"\*\*When:\*\*\s*(\S+)")
#: One entry: a `## ` heading and everything until the next one. Found rather than split, because splitting
#: on the heading loses whether the file opened with one and the first entry goes with the preamble.
ENTRY = re.compile(r"^## .*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
BANNER = ("<!-- Rendered from fairways/*/{name} by `make decisions`. Never edit by hand: `make check-rendered`\n"
          "     refuses a file that is not what its sources render to. Edit the fairway's own copy. -->\n")


def entries(text: str) -> list[str]:
    """One string per `## ` entry, with whatever preamble the file has dropped."""
    return [found.group(0).rstrip() + "\n" for found in ENTRY.finditer(text)]


def ordered(parts: list[str]) -> list[str]:
    """Every entry, by the instant it records. Stable, so two entries of one instant keep their file's order."""
    return sorted(parts, key=lambda part: (WHEN.search(part) is None, (WHEN.search(part) or [None, ""])[1]))


def sources(name: str) -> list[Path]:
    return sorted(FAIRWAYS.glob(f"*/{name}")) if FAIRWAYS.is_dir() else []


def feature() -> str:
    """The feature in flight: the one directory under `specs/` with a slice record."""
    found = sorted(path.name for path in SPECS.glob("*/") if (path / "slices").is_dir()) if SPECS.is_dir() else []
    return found[0] if found else ""


def rendered(name: str) -> str:
    """What the feature-level file should hold, from every fairway's own copy."""
    parts: list[str] = []
    for path in sources(name):
        parts.extend(entries(path.read_text(encoding="utf-8")))
    return BANNER.format(name=name) + "\n" + "\n".join(ordered(parts))


def main(argv: list[str]) -> int:
    checking = "--check" in argv
    where = feature()
    if not where:
        print("render-fairways: no feature with a slice record yet; nothing to fold")
        return 0
    drifted = []
    for name in FOLDED:
        if not sources(name):
            continue
        path = SPECS / where / name
        meant = rendered(name)
        if checking:
            if not path.is_file() or path.read_text(encoding="utf-8") != meant:
                drifted.append(path.relative_to(ROOT).as_posix())
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(meant, encoding="utf-8")
        print(f"render-fairways: {path.relative_to(ROOT).as_posix()} from {len(sources(name))} fairway(s)")
    if drifted:
        print("render-fairways: a rendered file is not what its sources render to\n", file=sys.stderr)
        for path in drifted:
            print(f"  {path}: edited by hand, or a fairway's copy changed since it was folded", file=sys.stderr)
        print("\nRun: make decisions", file=sys.stderr)
        return 1
    if checking:
        print(f"render-fairways: the feature-level files are what fairways/*/ render to")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
