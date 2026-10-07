"""The deck log and the harbour log: one line per event, and the only thing that says what happened.

The first attempt had a runner that was the single source of status, and it died at iteration two. Seventeen
of nineteen iterations ran from interactive sessions afterwards and wrote nothing at all — no run log, no
stream, no line — so the checkpoint still said "iteration 2" while twenty slices merged. Nobody could answer
what the state was without reading git. In MANDA the same shape failed the other way: `model.yaml` said
`planned` for eight slices that were built and merged, because the field was written at plan time and never
reconciled.

Both are the same mistake, which is state kept somewhere other than where the work happened. A log line is
written by the thing that did the work at the moment it did it, and the rule that falls out of that is the
one the whole of version 2 rests on: **a slice that wrote no line made no progress**. Status is folded from
lines, never stored.

**Two logs, and the split between them is about writers, not about contents.** A fairway's captain writes
its own **deck log** and nothing else, so no two processes ever append to one file. The **harbour log** has
exactly one writer, the harbourmaster, which copies across the handful of lines other fairways need — a
mark set, a park, a flag change, a telegraph. That is why the one shared log never conflicts.

**Every line carries `v`.** A reader that meets a version it does not know refuses the line and names the
upgrade rather than guessing which fields moved. Silently skipping a line it could not parse would make a
log that is missing events look exactly like a log of a run that did not have them, and that is the failure
this file exists to prevent.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

#: The format every line declares. A reader refuses anything higher and names what reads it.
V = 1
#: Where a fairway's own log lives, and the one log every fairway reads. Both are ignored by git: heartbeat
#: and token lines arrive every few seconds and have no place in trunk's history. The harbourmaster syncs
#: them through `refs/slipwai/logs`, so a captain on another machine reads the same lines with no commit.
LOGS = ".slipwai/logs"
HARBOUR = f"{LOGS}/harbour.jsonl"

#: What every line carries, whichever log it is in.
COMMON = ("v", "t", "kind")

#: Each deck-log kind against the fields it must carry beyond the common ones. A fairway's captain writes
#: these, in its own file, and nothing else writes there.
DECK_KINDS: dict[str, tuple[str, ...]] = {
    "claimed": ("fairway", "slice"),
    # Written at the setting slice's first stage, in its own worktree. This is what clears a sibling, which
    # is why it is not `merged`: waiting for a merge would serialise every fairway behind every other.
    "mark-set": ("fairway", "slice", "mark"),
    "demo": ("fairway", "slice", "verdict"),
    # Against a capability rather than a slice: a person's demo is of a whole chunk of work (theme B, 10).
    "accepted": ("fairway", "capability"),
    "demo-due": ("fairway", "capability"),
    "merged": ("fairway", "slice", "commit"),
    "decision": ("fairway", "id", "what"),
    "told": ("fairway", "message"),
    # Carries the `t` of the `told` it answers, which is what makes it a receipt rather than an assertion.
    "read": ("fairway", "told"),
    "heartbeat": ("fairway",),
    "stowed": ("fairway", "slice", "from", "what"),
    "parked": ("fairway", "why"),
}

#: Each harbour-log kind. Only the harbourmaster writes these, which is how one shared file never conflicts.
HARBOUR_KINDS: dict[str, tuple[str, ...]] = {
    "mark-set": ("fairway", "slice", "mark"),
    "flag-hoisted": ("flag", "where"),
    "flag-struck": ("flag",),
    "berth-allocated": ("fairway", "berth"),
    "fires-banked": ("step", "why"),
    "park": ("fairway", "why"),
    "telegraph": ("position",),
}


class Unreadable(Exception):
    """A line this reader cannot be trusted with. Never swallowed: a log missing the events it could not
    parse reads exactly like a log of a run that did not have them."""


def now() -> str:
    """The timestamp a line carries: UTC, to the second, which is what sorts two logs into one order."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Entry:
    """One event, in whichever log its kind belongs to."""

    kind: str
    fields: dict = field(default_factory=dict)
    t: str = ""
    v: int = V

    def line(self) -> str:
        """The line as it is appended: one JSON object, one `\\n`, no indentation.

        Written with `O_APPEND` and one `write()` per line by whoever calls this, so two processes
        interleave whole lines rather than tearing one.
        """
        body = {"v": self.v, "t": self.t or now(), "kind": self.kind, **self.fields}
        return json.dumps(body, ensure_ascii=False, sort_keys=False) + "\n"


def declared(kind: str, harbour: bool = False) -> tuple[str, ...]:
    """The fields a kind must carry, or a refusal naming the log it was looked for in."""
    kinds = HARBOUR_KINDS if harbour else DECK_KINDS
    if kind not in kinds:
        where = "the harbour log" if harbour else "a deck log"
        raise Unreadable(f"{kind!r} is not a kind {where} has. Its kinds are: {', '.join(sorted(kinds))}")
    return kinds[kind]


def entry(kind: str, harbour: bool = False, **fields: object) -> Entry:
    """One entry, with every field its kind declares, or a refusal naming what is missing.

    Checked on the way in rather than on the way out: a line that is written short is a line some reader
    weeks later cannot use, and by then nobody knows what the missing value was.
    """
    required = declared(kind, harbour)
    missing = [name for name in required if name not in fields]
    if missing:
        raise Unreadable(f"a {kind!r} line carries {', '.join(required)}; this one has no "
                         f"{', '.join(missing)}")
    return Entry(kind=kind, fields=dict(fields))


def read(line: str, harbour: bool = False) -> Entry:
    """One line back, or a refusal that says which rule it broke and what to do about it."""
    text = line.strip()
    if not text:
        raise Unreadable("an empty line")
    try:
        body = json.loads(text)
    except ValueError as fault:
        raise Unreadable(f"not JSON: {fault}") from fault
    if not isinstance(body, dict):
        raise Unreadable("a line is one JSON object")
    version = body.get("v")
    if version != V:
        raise Unreadable(
            f"this line says v{version} and this reader knows v{V}. A newer slipwai wrote it: "
            f"upgrade with `slipwai upgrade` rather than reading it with this one, which would have to "
            f"guess which fields moved"
        )
    kind = str(body.get("kind", ""))
    required = declared(kind, harbour)
    missing = [name for name in required if name not in body]
    if missing:
        raise Unreadable(f"a {kind!r} line carries {', '.join(required)}; this one has no "
                         f"{', '.join(missing)}")
    known = {*COMMON, *required}
    return Entry(kind=kind, t=str(body.get("t", "")),
                 fields={name: value for name, value in body.items() if name not in known} |
                        {name: body[name] for name in required})


def deck_path(feature: str, fairway: str) -> str:
    """A fairway's own log. One writer, its captain, so two fairways never meet on one line."""
    return f"{LOGS}/{feature}/{fairway}.jsonl"


def fold(lines: list[str], harbour: bool = False) -> list[Entry]:
    """Every readable entry, in the order written. A line that cannot be read stops the fold.

    Deliberately not "skip what you cannot parse". A board folded from a log with holes in it is a board
    that is confidently wrong, and the first attempt's whole problem was a status nobody could check.
    """
    return [read(line, harbour) for line in lines if line.strip()]
