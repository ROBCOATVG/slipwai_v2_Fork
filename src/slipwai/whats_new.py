"""What you got, printed where you upgraded, read from the changelog the release carries.

An upgrade that says `Successfully installed slipwai-2.1.0` has told you a number. Finding out what the
number means is a web page, which means it is a thing most people never do — so the next time something
behaves differently they look for a bug rather than for a change.

**So the entries between the version you had and the version you got are printed, there and then.** Not a
link, and not everything: the ones you crossed. The changelog ships in the wheel and in the executable for
exactly this, which is also what `migrate` reads its catch-up notes from.

**Crossing a major version is told as a crossing.** Moving from 1.x to 2.x is not a longer list of the same
kind of thing. It is a different factory — the languages are packages, the loop has captains, the state is
in the logs — and a person who meets that as eleven paragraphs of changelog will meet it instead as a day
of confusion. So that one gets a banner, the shape of what changed in five lines, and the one command that
moves a project across.

**What is not known is said.** An upgrade whose changelog has no entry for the version you landed on prints
that, rather than printing nothing and leaving "did it work?" as the question.
"""
from __future__ import annotations

import re
from pathlib import Path

from .assets import ROOT
from .versions import key, parse

CHANGELOG = ROOT / "CHANGELOG.md"
#: `## 2.1.0 — MINOR`, as `changelog.entry` writes it.
HEADING = re.compile(r"^## (?P<version>\S+)(?: — (?P<level>PATCH|MINOR|MAJOR))?\s*$")
#: How many entries are printed before the rest are counted rather than shown. An upgrade that crossed
#: fifteen releases is a person who has been away, and fifteen entries is a wall they will scroll past.
SHOWN = 5

CROSSING = """
   ╭───────────────────────────────────────────────────────────────╮
   │                                                               │
   │   slipwai 2 — a different factory, not a bigger one           │
   │                                                               │
   ╰───────────────────────────────────────────────────────────────╯

Five things are not where you left them.

  Languages are packages.   `slipwai search`, `slipwai install go`. The keel ships none, so a
                            language can be released on its own day.
  Extensions are packages.  Same chandlery, same four verbs, elected at `./init`.
  The loop has captains.    One per stream, each believing the log and not the agent. The thing
                            you type starts them and exits; nothing holds the state of a run.
  The state is in the log.  A stage that wrote no line made no progress. `slipwai fleet` folds
                            the board out of the logs and keeps nothing of its own.
  There is one lever.       `slipwai telegraph half-ahead` sets every number a run is held to.

What it costs you:

  slipwai migrate           in each project. It moves what is there, names what it moved, and
                            installs the languages that project's services are written in.

Your 1.x projects keep working until you run it. Nothing is migrated behind your back.
"""


def entries(text: str) -> list[tuple[str, str, str]]:
    """Every entry in a changelog, newest first: (version, level, prose)."""
    found: list[tuple[str, str, str]] = []
    version, level = "", ""
    body: list[str] = []
    for line in text.splitlines():
        match = HEADING.match(line)
        if match:
            if version:
                found.append((version, level, "\n".join(body).strip()))
            version, level, body = match.group("version"), match.group("level") or "", []
        elif version:
            body.append(line)
    if version:
        found.append((version, level, "\n".join(body).strip()))
    return found


def read(path: Path | None = None) -> list[tuple[str, str, str]]:
    """The changelog this copy carries, or nothing where it carries none."""
    place = path or CHANGELOG
    try:
        return entries(place.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return []


def between(found: list[tuple[str, str, str]], had: str, got: str) -> list[tuple[str, str, str]]:
    """The entries crossed: above the version you had, at or below the version you got."""
    return [one for one in found if key(had) < key(one[0]) <= key(got)]


def major_of(version: str) -> int | None:
    match = parse(version)
    return int(match.group(1)) if match else None


def crossed_major(had: str, got: str) -> bool:
    """Whether this upgrade moved across a major version."""
    before, after = major_of(had), major_of(got)
    return before is not None and after is not None and after > before


def crossing_into_two(had: str, got: str) -> bool:
    """Whether this is the 1 → 2 crossing, which is the one `CROSSING` is written about.

    Written about, not generated: the banner says what version 2 *is*, which is a thing somebody wrote
    once and not a thing arithmetic can produce. A 2 → 3 crossing is a major like any other here until
    somebody writes its own, and until then it gets the entries and a line saying it was a major.
    """
    return major_of(had) == 1 and major_of(got) == 2


def lines(had: str, got: str, found: list[tuple[str, str, str]] | None = None) -> list[str]:
    """What `slipwai upgrade` prints after it has moved: what you got, in the words of the changelog."""
    held = read() if found is None else found
    if crossing_into_two(had, got):
        return [*CROSSING.strip("\n").splitlines(), "",
                f"You were on {had}. You are on {got}."]
    major = ([f"{had} → {got} crosses a major version: things have moved, not just changed.", ""]
             if crossed_major(had, got) else [])
    crossed = between(held, had, got)
    if not crossed:
        return [*major,
                f"{got} is installed. Its changelog entry is not in this copy, so what changed is not "
                f"something this can tell you — `slipwai --version` confirms what you have, and "
                f"CHANGELOG.md in the release says the rest"]
    said = [*major, f"What you got, {had} → {got}:", ""]
    for version, level, body in crossed[:SHOWN]:
        said.append(f"  {version}" + (f" — {level}" if level else ""))
        said += [f"    {line}" if line.strip() else "" for line in body.splitlines()]
        said.append("")
    left = len(crossed) - SHOWN
    if left > 0:
        said.append(f"  …and {left} more release(s) in CHANGELOG.md")
    return said
