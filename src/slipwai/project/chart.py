"""Clearance: the rule that lets a slice start, read off the chart and the deck logs and nothing else.

Version 1's rule was "its own contract is settled", which a slice could only answer about itself. That
serialised a fresh fairway: every slice needed a host example map before any of them could run, because
nothing said what a slice was waiting *for*. Issue #32 asked for the rule this module is.

A slice has clearance when every mark it steers by has been set. A mark is set when some slice wrote a
`mark-set` line for it, which it does as its own first stage, inside its own worktree — so a fairway is
unblocked by a sibling that has *planned*, not by one that has merged. That is the whole of the parallelism
this plan promises, and it is three lines of rule over two files nobody has to agree about.

**State comes from the log, never from a status field.** In the first attempt `model.yaml` said `planned`
for eight slices that were built and merged, because the field was written at plan time and never
reconciled. A log line is written by the thing that did the work, at the moment it did it, and a slice that
wrote no line made no progress. So this reads lines.

The captain (slice 7.2) and `/drive` both call `cleared`, and both want the same two things from it: whether
to start, and — when not — the sentence to put in front of a person. So the refusal is the return value
rather than a log line somewhere else, and it names every mark that is missing rather than the first,
because a fairway told one blocker at a time is a fairway blocked once per blocker.
"""
from __future__ import annotations

from collections.abc import Iterable

#: The deck-log line that says a mark now exists. Written by the slice that owns the mark, at its first
#: stage, before anything is built against it (slice 5.13 gives the line its schema).
MARK_SET = "mark-set"


def marks_set(lines: Iterable[dict]) -> set[str]:
    """Every mark some slice has set, from the deck logs handed in.

    A line that is not a `mark-set`, or carries no `mark`, is not this function's business: the logs hold
    eleven kinds and a reader that refused the ones it did not know would break every time one was added.
    """
    return {str(line["mark"]) for line in lines
            if isinstance(line, dict) and line.get("kind") == MARK_SET and line.get("mark")}


def steered_by(chart: dict, slice_id: str) -> list[str]:
    """The marks this slice builds against, in the order the chart names them."""
    slices = chart.get("slices")
    entry = slices.get(slice_id) if isinstance(slices, dict) else None
    steers = entry.get("steers_by") if isinstance(entry, dict) else None
    return [str(mark) for mark in steers] if isinstance(steers, list) else []


def setter_of(chart: dict, mark: str) -> str | None:
    """Which slice owns a mark. One of them does: `check-chart` refuses a mark two slices set."""
    slices = chart.get("slices")
    for slice_id, entry in (slices.items() if isinstance(slices, dict) else []):
        if isinstance(entry, dict) and mark in [str(name) for name in entry.get("sets") or []]:
            return str(slice_id)
    return None


def cleared(chart: dict, lines: Iterable[dict], slice_id: str) -> bool | str:
    """`True` where this slice may start, or the sentence saying what it is waiting for and on whom.

    A slice the chart does not name is refused rather than cleared. Clearance is a statement about a slice
    the chart knows; answering `True` for one it does not would clear anything anybody asked about.
    """
    slices = chart.get("slices")
    if not isinstance(slices, dict) or slice_id not in slices:
        return f"{slice_id} is not on the chart, so nothing says what it steers by"
    have = marks_set(lines)
    waiting = [mark for mark in steered_by(chart, slice_id) if mark not in have]
    if not waiting:
        return True
    owed = []
    for mark in waiting:
        setter = setter_of(chart, mark)
        owed.append(f"{mark} (set by {setter})" if setter else f"{mark} (no slice sets it — the chart is wrong)")
    return f"{slice_id} steers by {', '.join(owed)}, and none of those is set yet"


def cleared_slices(chart: dict, lines: Iterable[dict]) -> list[str]:
    """Every slice that may start now, in the chart's own order, which is split order."""
    slices = chart.get("slices")
    known = list(slices) if isinstance(slices, dict) else []
    settled = marks_set(lines)
    return [slice_id for slice_id in known
            if all(mark in settled for mark in steered_by(chart, str(slice_id)))]
