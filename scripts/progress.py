#!/usr/bin/env python3
"""Tick off the slices the history says are done, in the plan's own tables.

A plan that records its own progress by hand is a plan that is wrong by Friday. This reads `git log` and
writes a Status column in each phase's table of `docs/slipwai-2-plan.md`. Nothing claims to be done that
is not in the history, and nothing in the history goes unticked.

What counts as landed is the trailer `Slice-done: <n>.<m>`, not the subject line. The subject was the
first thing tried and it was wrong within an hour: the commit that *added* slice 9.5 to the plan was
written `Slice 9.5: the three contributor skills…`, and the ticker marked a slice done whose work had not
started. A trailer is deliberate. A subject is a sentence, and a sentence can be about a slice without
being the slice.

`--check` compares the committed plan against what this would write and fails if they differ, which is
what `tests/test_progress.py` runs. Finish a slice, run `make progress`, commit both.

A slice is done when its commit is an ancestor of the branch this runs on. A slice still on its own branch
is not done — rule 10 says people hold the merge, so the merge is what done means.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/slipwai-2-plan.md"
SECTION = "## 11. The implementation plan"
TRAILER = re.compile(r"^Slice-done: (\d+\.\d+[a-z]?)\s*$", re.MULTILINE)
# The slices that landed before the trailer existed, by the commit that landed each. Written once, on
# 2026-10-06, and never added to: everything after carries its own trailer.
BEFORE_THE_TRAILER = {
    "1.1": "5209785", "1.2": "0ba7af6", "1.3": "a6ef34f", "1.4": "941f7c8",
    "1.5": "7001d7c", "1.6": "37cf944", "2.2": "1841091", "2.7": "357700a",
}
ROW = re.compile(r"^\| (\d+\.\d+[a-z]?) \|")
DONE, TODO = "done", ""


def shipped() -> dict[str, str]:
    """Each slice the history has landed, by id, with the short hash of the commit that landed it."""
    log = subprocess.run(
        ["git", "log", "--format=%h%x1e%B%x1f"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    found: dict[str, str] = {}
    for entry in log.split("\x1f"):
        short, _, message = entry.strip().partition("\x1e")
        for slice_id in TRAILER.findall(message):
            found.setdefault(slice_id, short)  # the first landing, not a later touch
    return {**{k: v for k, v in BEFORE_THE_TRAILER.items() if has(v)}, **found}


def has(short: str) -> bool:
    """Whether a commit of `BEFORE_THE_TRAILER` is an ancestor of what is checked out, so a branch that
    predates one does not claim its slice."""
    done = subprocess.run(
        ["git", "merge-base", "--is-ancestor", short, "HEAD"], cwd=ROOT, capture_output=True
    )
    return done.returncode == 0


def ticked(page: str, done: dict[str, str]) -> str:
    """The plan with every slice table carrying a Status column that the history, not a person, fills in.

    Each line is stripped of the column this script last wrote before the new one is added, so running it
    twice leaves the page exactly as running it once did. A table that grows a column per run is the
    classic shape of this bug.
    """
    lines = page.splitlines()
    start = lines.index(SECTION)
    out = lines[:start]
    for line in lines[start:]:
        if line.startswith("| Slice |"):
            out.append(without_status(line) + " Status |")
        elif re.fullmatch(r"\|(-+\|)+", line) and out[-1].endswith(" Status |"):
            # Built from the header rather than edited: a separator cell is `---` whichever column it is,
            # so stripping "the one this script wrote" would take a real column on the first run.
            out.append("|" + "---|" * (out[-1].count("|") - 1))
        elif match := ROW.match(line):
            short = done.get(match.group(1))
            out.append(without_status(line) + (f" {DONE} {short} |" if short else f" {TODO} |"))
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def without_status(row: str) -> str:
    """A header or row with the Status cell this script last wrote removed, and nothing else touched.

    Not for separators: `---` is what every cell of one holds, so there is no telling this script's from
    a real column. `ticked` rebuilds those from the header's width instead.
    """
    body = row.rstrip()
    if re.search(r"\|\s*(done [0-9a-f]{7,}|Status|)\s*\|$", body):
        body = body[: body.rstrip().rfind("|", 0, len(body) - 1) + 1]
    return body


def summary(page: str, done: dict[str, str]) -> str:
    """One line under section 11's heading saying how far the build has got, by phase."""
    ids = [m.group(1) for line in page.splitlines() if (m := ROW.match(line))]
    phases: dict[str, list[str]] = {}
    for slice_id in ids:
        phases.setdefault(slice_id.split(".")[0], []).append(slice_id)
    parts = [
        f"phase {phase} {sum(1 for i in found if i in done)}/{len(found)}"
        for phase, found in sorted(phases.items(), key=lambda kv: int(kv[0]))
    ]
    return (
        f"**Progress: {sum(1 for i in ids if i in done)} of {len(ids)} slices done** — "
        + ", ".join(parts)
        + ". Written by `scripts/progress.py` from the history; run `make progress` after a slice merges."
    )


def rendered() -> str:
    page = PLAN.read_text(encoding="utf-8")
    done = shipped()
    page = ticked(page, done)
    line = summary(page, done)
    lines = page.splitlines()
    at = lines.index(SECTION) + 1
    if at + 1 < len(lines) and lines[at + 1].startswith("**Progress:"):
        lines[at + 1] = line
    else:
        lines[at:at] = ["", line]
    return "\n".join(lines) + "\n"


def main(arguments: list[str]) -> int:
    wanted = rendered()
    if "--check" not in arguments:
        PLAN.write_text(wanted, encoding="utf-8")
        print(summary(wanted, shipped()).split(" — ")[0].replace("**", ""))
        return 0
    if PLAN.read_text(encoding="utf-8") == wanted:
        print("progress: the plan's ticks match the history")
        return 0
    print("progress: the plan's ticks are out of step with the history.\n  Run: make progress", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
