#!/usr/bin/env python3
"""The captain: the outer loop for one fairway, and the thing that believes the log rather than the agent.

`cruise.py` ran one iteration per checkout and trusted what the iteration said about itself. It died at
iteration two, and the seventeen iterations that followed ran from interactive sessions and wrote nothing —
so the checkpoint still said "iteration 2" while twenty slices merged. The inversion this file is built on
falls straight out of that: **a stage that wrote no line made no progress**, and every control here reads
lines rather than asking the thing being controlled how it is getting on.

Each turn it: fetches trunk and both logs; derives the fairway's state from its own `claimed` and `merged`
lines; picks the next slice in split order that `clearance.py` allows; writes `claimed`; dispatches `/drive`
for that slice in its berth; watches the deck log while it runs; reads the inbox at every boundary and
enforces the receipt; and asks the harbourmaster for the merge, because a captain holds no credential.

**Nothing it relies on is in the agent's answer.** Progress is a new line in the deck log. A stage that has
written nothing for its wall budget is ended and `parked` with the reason — not because the agent said it was
stuck, which a stuck agent cannot say, but because the log stopped.

**And a slice is through its gate only when the log says so, in lines written during this turn.** That rule
was applied to the wall budget and nowhere else, so the first real run had `/drive` print a help message,
exit 0, and this file write `claimed`, then `request: merge`, and report the slice through its gate — with
no `mark-set` and no `demo` anywhere. What closes a slice now is every mark the chart says it `sets`, plus a
`demo`, all after the index this turn started at. *During this turn* is the whole of it: without it a retry
passes on the previous turn's lines, which is the same fault as a cursor that outlives its log.

A demo that came back `behaviour` or `implementation` is not a park, it is a retry. The person who sent it
back is present and has just written notes, and parking would ask them to come back and restart a fairway
before anything acts on them. `/drive` re-enters at the first incomplete stage, so a retry resumes at the
demo rung with the notes in the slice. `attempts` in `harbour.json` bounds it; when it is spent the fairway
parks naming the verdict and the count.

**A hook never costs the rung.** The extension hook points fire around each rung, at each boundary and before
a merge; `hooks.py` always exits 0 for them, and the captain does not read their output. A hook is a second
belt, and a second belt that can stop the run is the thing it was meant to be instead of.

Standalone and dependency-free: this runs inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import clearance  # noqa: E402
import inbox  # noqa: E402
import logs  # noqa: E402


def project_root() -> Path:
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


ROOT = project_root()
HARBOUR = ROOT / "harbour.json"
HOOKS = ROOT / "scripts/extensions/hooks.py"
#: How often a heartbeat is written while a slice is being worked. Short enough that a fleet board can tell a
#: wedged berth from a slow one, long enough that it is not most of the log.
HEARTBEAT = 60.0
#: How often the deck log is re-read while `/drive` runs. The log is the only progress signal there is.
POLL = 2.0
#: Used where `harbour.json` is absent or unreadable — the file is the answer, and these keep the loop
#: bounded while somebody fixes it rather than letting an unbounded stage be the cost of a typo.
DEFAULT_STAGE_MINUTES = 30
#: Re-dispatches of `/drive` for one slice, where `harbour.json` does not say. `half-ahead`'s number, which
#: is what a fresh harbour is at.
DEFAULT_ATTEMPTS = 2
#: The verdict that closes a slice, and the two that send it back. `logs.VERDICTS` is the whole set.
ACCEPTED = "accepted"


def harbour() -> dict:
    try:
        held = json.loads(HARBOUR.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) else {}


def stage_bound() -> float:
    """Seconds a stage may write nothing before it is ended. The longest stage's budget, because the captain
    cannot tell from outside which stage is running — only that the log has stopped."""
    stages = harbour().get("stages")
    minutes = [row.get("minutes") for row in stages.values()
               if isinstance(row, dict)] if isinstance(stages, dict) else []
    found = [one for one in minutes if isinstance(one, int | float) and one > 0]
    return (max(found) if found else DEFAULT_STAGE_MINUTES) * 60.0


def attempts() -> int:
    """Re-dispatches of `/drive` one slice may have. `0` means one run and no retry."""
    held = harbour().get("attempts")
    return held if isinstance(held, int) and held >= 0 else DEFAULT_ATTEMPTS


def deck(feature: str, fairway: str) -> Path:
    return ROOT / logs.deck_path(feature, fairway)


def entries(feature: str, fairway: str) -> list[logs.Entry]:
    path = deck(feature, fairway)
    if not path.is_file():
        return []
    try:
        return logs.fold(path.read_text(encoding="utf-8").splitlines())
    except logs.Unreadable as fault:
        raise SystemExit(f"captain: {path} cannot be read ({fault}). The log is the state, so this is not "
                         f"something to carry on past: fix the line and start the captain again")


def write(feature: str, fairway: str, entry: logs.Entry) -> None:
    """Append one line to this fairway's own log. One writer per file, so nothing is locked."""
    path = deck(feature, fairway)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(entry.line())


def state(found: list[logs.Entry]) -> tuple[set[str], set[str], str]:
    """(claimed, merged, why it is parked) — the fairway, as its own lines say it is."""
    claimed = {str(e.fields["slice"]) for e in found if e.kind == "claimed"}
    merged = {str(e.fields["slice"]) for e in found if e.kind == "merged"}
    parked = next((str(e.fields["why"]) for e in reversed(found) if e.kind == "parked"), "")
    return claimed, merged, parked


def next_slice(fairway: str, claimed: set[str], merged: set[str]) -> tuple[str | None, str]:
    """The next slice this fairway may start, and why there is none where there is none.

    Split order, not sorted order: wiring is the one place two slices can depend on each other's having run,
    and the chart's own order is the order the split agreed.
    """
    charted, feature = clearance.chart()
    settled = clearance.marks_set(feature)
    mine = [slice_id for slice_id, body in (charted.get("slices") or {}).items()
            if str((body or {}).get("fairway", "")) == fairway]
    if not mine:
        return None, f"the chart gives {fairway} no slices"
    left = [slice_id for slice_id in mine if slice_id not in merged and slice_id not in claimed]
    if not left:
        return None, f"every slice of {fairway} is claimed or merged"
    for slice_id in left:
        if clearance.cleared(charted, settled, slice_id) is True:
            return slice_id, ""
    waiting = clearance.cleared(charted, settled, left[0])
    return None, f"{left[0]} waits on {waiting}"


def fire(point: str, **given: str) -> None:
    """One hook point, which never costs the rung. `hooks.py` exits 0 whatever a hook did; this does not
    even read its output, so an extension cannot change what the captain does next."""
    if not HOOKS.is_file():
        return
    argv = [sys.executable, str(HOOKS), point]
    for name, value in given.items():
        argv += [f"--{name}", value]
    subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)


def drive_command(slice_id: str, fairway: str) -> list[str]:
    """What runs the ladder for one slice. `SLIPWAI_DRIVE` replaces it, which is how a test drives a fake
    and how a harness other than the default one is pointed at."""
    named = os.environ.get("SLIPWAI_DRIVE")
    if named:
        return [*named.split(), slice_id, fairway]
    return [sys.executable, str(HERE / "drive.py"), slice_id, fairway]


def watched(process: subprocess.Popen, feature: str, fairway: str, bound: float,
            started: int) -> tuple[bool, str]:
    """Wait for `/drive`, writing a heartbeat and ending it if the log stops. (finished, why it was ended).

    What is watched is the log and not the process: a process that is alive and writing nothing is exactly
    the failure that cost the first attempt seventeen iterations, and it looks identical from the outside to
    one that is working hard.
    """
    last_line, last_beat = time.monotonic(), time.monotonic()
    seen = started
    while process.poll() is None:
        time.sleep(POLL)
        now = time.monotonic()
        count = len(entries(feature, fairway))
        if count > seen:
            seen, last_line = count, now
        if now - last_beat >= HEARTBEAT:
            write(feature, fairway, logs.entry("heartbeat", fairway=fairway))
            last_beat, seen = now, len(entries(feature, fairway))
        if now - last_line >= bound:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
            return False, (f"nothing was written to the deck log for {bound / 60:.0f} minutes, so the stage "
                           f"was ended. A stage that wrote no line made no progress")
    return process.returncode == 0, ("" if process.returncode == 0
                                     else f"`/drive` exited {process.returncode}")


def boundary(feature: str, fairway: str) -> str:
    """The inbox at a boundary, and why the fairway stops where it does.

    `inbox.owed` says a boundary is forced; this says what the next thing to happen is. Either way it is a
    person — a message nobody answered inside its bound, or a backlog of decisions nobody has read. The
    experiment reached 125 decisions with 105 of them never reviewed, which is not a record of judgement.
    """
    fire("boundary", slice="", fairway=fairway)
    owed = inbox.owed(fairway)
    if not owed.get("forced"):
        return ""
    late = owed.get("overrun") or []
    if late:
        said = str(late[0].get("message", ""))[:120]
        return (f"{len(late)} message(s) from a person have gone past the wait bound unanswered, the "
                f"oldest being {said!r}. `/told` reads them, and a read line is the receipt")
    return (f"{len(owed.get('unreviewed') or [])} decisions stand unread, over the ceiling of "
            f"{owed.get('ceiling')}. A backlog of judgement nobody has looked at is not judgement")


def sets_of(slice_id: str) -> list[str]:
    """The marks the chart says this slice publishes, which is what its gate is.

    An absent `sets` reads as none here and is refused by `make check-chart` once the split has run, where
    it can say which slice and what to write. This is the reader, not the gate.
    """
    charted, _ = clearance.chart()
    body = (charted.get("slices") or {}).get(slice_id) or {}
    return [str(mark) for mark in (body.get("sets") or [])]


def owed(fresh: list[logs.Entry], slice_id: str, promised: list[str]) -> tuple[list[str], str]:
    """What this slice still owes from the lines written this turn: (marks not set, the demo's verdict).

    The verdict is `""` where no demo was written at all, which is a different fault from one that was
    written and sent back — the first says the rung never ran, the second says a person watched it and
    wanted something changed, and they get different answers.
    """
    mine = [e for e in fresh if str(e.fields.get("slice", "")) == slice_id]
    done = {str(e.fields["mark"]) for e in mine if e.kind == "mark-set"}
    verdicts = [str(e.fields["verdict"]) for e in mine if e.kind == "demo"]
    return [mark for mark in promised if mark not in done], (verdicts[-1] if verdicts else "")


def dispatch(slice_id: str, feature: str, fairway: str) -> tuple[bool, str, list[logs.Entry]]:
    """One run of `/drive`, and the lines it wrote. (finished, why not, the lines written during it)."""
    fire("before-stage", stage="drive", slice=slice_id, fairway=fairway)
    started = len(entries(feature, fairway))
    process = subprocess.Popen(drive_command(slice_id, fairway), cwd=ROOT)
    finished, why = watched(process, feature, fairway, stage_bound(), started)
    fire("after-stage", stage="drive", slice=slice_id, fairway=fairway)
    return finished, why, entries(feature, fairway)[started:]


def work(slice_id: str, feature: str, fairway: str) -> tuple[bool, str]:
    """One slice, start to finish. (did it finish, why it did not)."""
    write(feature, fairway, logs.entry("claimed", fairway=fairway, slice=slice_id))
    promised = sets_of(slice_id)
    bound, sent_back = attempts(), 0
    while True:
        finished, why, fresh = dispatch(slice_id, feature, fairway)
        if not finished:
            return False, why
        missing, verdict = owed(fresh, slice_id, promised)
        if not missing and verdict == ACCEPTED:
            break
        if verdict and verdict != ACCEPTED:
            sent_back += 1
            if sent_back <= bound:
                continue
            return False, (f"the demo came back {verdict!r} {sent_back} time(s), which is what `attempts` "
                           f"allows. The notes are in the slice; a person decides what happens next")
        if missing:
            return False, (f"the chart says {slice_id} sets {', '.join(promised)}, and this turn wrote no "
                           f"`mark-set` for {', '.join(missing)}. A stage that wrote no line made no "
                           f"progress, so nothing here is evidence the slice was built")
        return False, (f"this turn wrote no `demo` line for {slice_id}, so nothing says a person watched it "
                       f"work. `/drive` exiting 0 is the agent's account of itself, which is the one thing "
                       f"this loop does not read")
    held = boundary(feature, fairway)
    if held:
        return False, held
    fire("before-merge", slice=slice_id, fairway=fairway)
    write(feature, fairway, logs.entry(
        "request", fairway=fairway, id=f"merge-{slice_id}", what="merge",
        detail=f"merge slice/{slice_id} into trunk after the full gate"))
    return True, ""


def fetch() -> None:
    """Trunk and both logs. Never fatal: a harbour on one machine has no remote to fetch from."""
    for argv in (["git", "fetch", "--quiet", "origin"],
                 ["git", "fetch", "--quiet", "origin", "refs/slipwai/logs/*:refs/slipwai/logs/*"]):
        subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)


def turn(fairway: str) -> str:
    """One turn: what happened, as the line the command prints."""
    fetch()
    _, feature = clearance.chart()
    found = entries(feature, fairway)
    claimed, merged, parked = state(found)
    if parked:
        return f"captain: {fairway} is parked — {parked}"
    slice_id, why = next_slice(fairway, claimed, merged)
    if slice_id is None:
        return f"captain: nothing to start in {fairway} — {why}"
    done, fault = work(slice_id, feature, fairway)
    if done:
        return f"captain: {slice_id} is through its gate; the merge is asked of the harbourmaster"
    write(feature, fairway, logs.entry("parked", fairway=fairway, why=f"{slice_id}: {fault}"))
    return f"captain: {fairway} parked at {slice_id} — {fault}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="captain", description="Run one fairway: claim, dispatch, watch the log, ask for the merge")
    parser.add_argument("fairway", help="the fairway this captain is for, as the chart names it")
    parser.add_argument("--once", action="store_true", help="one slice, rather than the loop")
    parser.add_argument("--interval", type=float, default=30.0, help="seconds between turns")
    parsed = parser.parse_args(argv)
    while True:
        said = turn(parsed.fairway)
        print(said, flush=True)
        if parsed.once or " is parked — " in said or "nothing to start" in said:
            return 0
        time.sleep(parsed.interval)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
