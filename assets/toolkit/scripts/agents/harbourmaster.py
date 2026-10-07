#!/usr/bin/env python3
"""The harbourmaster: the one writer of the harbour log, and the only thing in a harbour that holds a credential.

One process per harbour. Its job is two things that both come from the same rule — **one writer per file** —
and a third that comes from a different one.

**It carries between fairways.** A captain writes its own deck log and reads everybody's, but a fairway that
had to read every other fairway's log to find the one line it needed would be reading a hundred files to find
three. So the handful of lines that matter across fairways — a mark set, a park, a berth allocated, a flag
changed — are copied into the harbour log, which has exactly one writer and therefore never conflicts.

**It allocates berths.** A captain asks by writing `berth-request`; the answer is `berth-allocated` in the
harbour log. The numbers are arithmetic (`berths.py`), so nobody chooses one and nobody chooses the same one
twice — but somebody has to decide the order, and one writer deciding it is the whole of the mechanism.

**It holds the credentials, and that is the different rule.** A berth is a sandbox; a berth with a token in
it is a sandbox with a way out. So a captain asks for a push, a merge, a deploy, a flag change or a publish
by writing a `request` line, and this process does it or refuses with the reason. What it will never do is a
closed list, and it is checked against the request's own text rather than trusted to the asker:

    destroy data or history · release what nobody asked for · spend money · expose a secret ·
    weaken security · discard a person's commits · change a gate to make it pass

**Both outcomes are written.** A refusal that left no line is one the captain waits on for ever and nobody
can explain afterwards. That is the same rule as every other log line here: a thing that wrote no line did
not happen.

Standalone and dependency-free, like everything under `scripts/`: this runs inside a generated project, which
has no slipwai to import. `logs.py` and `berths.py` beside it are the keel's own modules, carried here by
`make shared` and byte-identical to their source.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import berths  # noqa: E402
import logs  # noqa: E402
import telegraph  # noqa: E402


def project_root() -> Path:
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


ROOT = project_root()
#: Where this process keeps how far it has read each deck log. A cursor, not a copy: the logs are the truth
#: and this is only a bookmark, so losing it costs a re-read and never a line.
CURSORS = ROOT / ".slipwai/harbourmaster.json"
#: The numbers this harbour is held to, and the lever over them. Watched rather than read once: a person
#: rings the telegraph while the run is going, which is the only time ringing it is any use.
HARBOUR_CONFIG = ROOT / "harbour.json"
#: Which deck-log kind becomes which harbour-log kind. Everything not here stays in the fairway's own log,
#: because the harbour log is what every captain reads on every turn and a line nobody needs is a line
#: everybody pays for.
CARRIED = {"mark-set": "mark-set", "parked": "park"}
#: What a request may ask for at all. A closed set: an action nobody wrote down is one nobody reviewed.
ACTIONS = ("push", "merge", "deploy", "flag", "publish")
#: What is never done, whoever asks and whatever the reason. Matched against the request's own text, because
#: the asker is the thing being checked and its own summary of what it is asking is not evidence.
NEVER: tuple[tuple[str, str], ...] = (
    (r"\bpush\b[^\n]*--force(?!-with-lease)", "a plain force-push discards somebody's commits"),
    (r"\bgit\s+reset\s+--hard\b", "a hard reset discards work that is not yours to discard"),
    (r"\bgit\s+clean\b", "a clean deletes files nobody has read"),
    (r"\bbranch\s+-D\b|\bpush\b[^\n]*--delete\b", "deleting a branch destroys history"),
    (r"\bdrop\s+(table|database|schema)\b|\btruncate\s+table\b", "that destroys data"),
    (r"\brm\s+-rf\b", "that destroys data"),
    (r"\bfilter-branch\b|\bfilter-repo\b|\brebase\b[^\n]*\b--root\b", "that rewrites history"),
    (r"(?i)\b(aws_secret|api[_-]?key|password|token)\s*=", "that puts a secret in a log line"),
    (r"(?i)\bdisable\b[^\n]*\b(tls|ssl|verification|signature|auth)", "that weakens security"),
    (r"(?i)--no-verify\b|--skip-checks?\b", "that skips the gate rather than passing it"),
)
HEARTBEAT = 15.0


def read_cursors() -> dict[str, int]:
    try:
        held = json.loads(CURSORS.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return {str(key): int(value) for key, value in held.items()} if isinstance(held, dict) else {}


def write_cursors(held: dict[str, int]) -> None:
    CURSORS.parent.mkdir(parents=True, exist_ok=True)
    CURSORS.write_text(json.dumps(held, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def deck_logs() -> list[Path]:
    """Every fairway's log, in a stable order. The harbour log is not one of them: it is the output."""
    place = ROOT / logs.LOGS
    harbour = ROOT / logs.HARBOUR
    return sorted(path for path in place.rglob("*.jsonl") if path.resolve() != harbour.resolve())


def new_lines(path: Path, cursors: dict[str, int]) -> tuple[list[str], int]:
    """The lines of this log the harbourmaster has not read, and where it has now read to."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return [], cursors.get(str(path), 0)
    seen = cursors.get(key_of(path), 0)
    return lines[seen:], len(lines)


def key_of(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def config() -> dict:
    try:
        held = json.loads(HARBOUR_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) else {}


def at() -> str:
    """Where the telegraph is, as the file says."""
    return str(config().get("position", telegraph.POSITIONS[0]))


def last_telegraph() -> str:
    """The position the harbour log last said, so a change is written once and not on every pass."""
    for entry in reversed(harbour_entries()):
        if entry.kind in ("telegraph", "fires-banked"):
            return str(entry.fields.get("position") or entry.fields.get("step") or "")
    return ""


def rung() -> list[logs.Entry]:
    """A `telegraph` line where the file has moved since the last one. Captains read it and adjust at their
    next boundary — not immediately, because a stage ended half-way to save a few tokens has saved nothing."""
    # No `harbour.json` is no telegraph, not `full-ahead`: writing a position into the log for a harbour
    # that never declared one would have the captains adjust to a lever nobody rang.
    if not HARBOUR_CONFIG.is_file():
        return []
    here = at()
    if here == last_telegraph() or here not in telegraph.SETTINGS:
        return []
    return [logs.entry("telegraph", harbour=True, position=here)]


def spent_today() -> int:
    """Thousands of input tokens the harbour has spent since midnight, from the lines that record it.

    From the logs rather than from a counter: a counter is state kept somewhere other than where the work
    happened, which is the mistake this whole method is built around not making.
    """
    today = logs.now()[:10]
    total = 0
    for path in deck_logs():
        try:
            found = logs.fold(path.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError, logs.Unreadable):
            continue
        for entry in found:
            tokens = entry.fields.get("tokens")
            if entry.t[:10] == today and isinstance(tokens, int | float):
                total += int(tokens)
    return total


def bank() -> list[logs.Entry]:
    """Step the position down one notch where the day's bunker is spent, or nothing.

    One notch at a time, and never straight to `stop`: a run that stops dead at the end of the day loses
    whatever was in flight, and a run that slows keeps finishing what it started.
    """
    here = at()
    allowed = config().get("bunker_per_day")
    if here not in telegraph.SETTINGS or not isinstance(allowed, int | float) or allowed <= 0:
        return []
    spent = spent_today()
    if spent < allowed:
        return []
    down = telegraph.slower(here)
    if down is None:
        return []
    write_position(down)
    return [logs.entry("fires-banked", harbour=True, step=down,
                       why=f"the day's bunker of {int(allowed)}k is spent ({spent}k), so the fires are "
                           f"banked one notch from {here}")]


def write_position(name: str) -> None:
    """Ring the telegraph down, in the file, so the next pass and every reader sees the same thing."""
    held = config()
    whole = telegraph.applied(name, held)
    if isinstance(held.get("stages"), dict):
        whole["stages"] = telegraph.scaled(held["stages"], float(whole["stage_scale"]))
    HARBOUR_CONFIG.write_text(json.dumps(whole, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def never(detail: str) -> str | None:
    """Why this request is one the harbourmaster will never do, or None."""
    for pattern, why in NEVER:
        if re.search(pattern, detail):
            return why
    return None


def answer(entry: logs.Entry) -> logs.Entry:
    """The harbour-log line one `request` gets: `granted` or `refused`, and always one of them."""
    fairway = str(entry.fields.get("fairway", ""))
    request = str(entry.fields.get("id", ""))
    what = str(entry.fields.get("what", ""))
    detail = str(entry.fields.get("detail", ""))
    if what not in ACTIONS:
        return logs.entry("refused", harbour=True, fairway=fairway, request=request,
                          why=f"{what!r} is not something a captain may ask for. It may ask for: "
                              f"{', '.join(ACTIONS)}")
    refusal = never(detail)
    if refusal is not None:
        return logs.entry("refused", harbour=True, fairway=fairway, request=request,
                          why=f"{refusal}. Asked: {detail}")
    return logs.entry("granted", harbour=True, fairway=fairway, request=request, what=what)


def allocation(fairway: str, taken: list[str]) -> logs.Entry:
    """The berth this fairway gets. Its index is its place in the order they were asked for, so two
    fairways never get one block and nobody chose a number."""
    name = berths.named(fairway.lower().replace("_", "-"))
    index = taken.index(name) if name in taken else len(taken)
    return logs.entry("berth-allocated", harbour=True, fairway=fairway,
                      berth=berths.berth(name, index).name)


def carried(entries: list[logs.Entry], taken: list[str]) -> list[logs.Entry]:
    """Every harbour-log line this batch of deck-log lines produces, in the order they were written."""
    written: list[logs.Entry] = []
    for entry in entries:
        if entry.kind in CARRIED:
            fields = dict(entry.fields)
            if entry.kind == "parked":
                written.append(logs.entry("park", harbour=True, fairway=fields["fairway"], why=fields["why"]))
            else:
                written.append(logs.entry(CARRIED[entry.kind], harbour=True, **fields))
        elif entry.kind == "berth-request":
            fairway = str(entry.fields["fairway"])
            written.append(allocation(fairway, taken))
            name = berths.named(fairway.lower().replace("_", "-"))
            if name not in taken:
                taken.append(name)
        elif entry.kind == "request":
            written.append(answer(entry))
    return written


def allocated_already() -> list[str]:
    """Every berth the harbour log has already allocated, in the order it did, so a restart repeats none."""
    taken: list[str] = []
    for entry in harbour_entries():
        if entry.kind == "berth-allocated":
            berth = str(entry.fields.get("berth", ""))
            if berth not in taken:
                taken.append(berth)
    return taken


def harbour_entries() -> list[logs.Entry]:
    path = ROOT / logs.HARBOUR
    if not path.is_file():
        return []
    try:
        return logs.fold(path.read_text(encoding="utf-8").splitlines(), harbour=True)
    except logs.Unreadable:
        return []


def append(entries: list[logs.Entry]) -> None:
    path = ROOT / logs.HARBOUR
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(entry.line())


def unreadable(path: Path, fault: str) -> None:
    """A deck log that cannot be read stops this pass over *that* log and says so. The others carry on: one
    fairway writing a bad line is not a reason the rest of the harbour stops hearing from each other."""
    print(f"harbourmaster: {key_of(path)} cannot be read ({fault}); its lines are not being carried",
          file=sys.stderr)


def once() -> int:
    """One pass: read what is new in every deck log, write what the harbour log needs. Returns lines written."""
    cursors = read_cursors()
    taken = allocated_already()
    written: list[logs.Entry] = []
    for path in deck_logs():
        lines, reached = new_lines(path, cursors)
        try:
            entries = logs.fold(lines)
        except logs.Unreadable as fault:
            unreadable(path, str(fault))
            continue
        written += carried(entries, taken)
        cursors[key_of(path)] = reached
    written += bank() or rung()
    if written:
        append(written)
    write_cursors(cursors)
    return len(written)


def fetch() -> None:
    """Bring in what other machines' captains have written. Never fatal: a harbour on one machine has no
    remote, and one that cannot reach its forge still has every local fairway to carry between."""
    run = subprocess.run(["git", "fetch", "--quiet", "origin", "refs/slipwai/logs/*:refs/slipwai/logs/*"],
                         cwd=ROOT, capture_output=True, text=True)
    if run.returncode != 0:
        said = (run.stderr or run.stdout).strip().splitlines()
        print(f"harbourmaster: the logs could not be fetched ({said[-1] if said else 'git failed'}); "
              f"carrying what is here", file=sys.stderr)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="harbourmaster",
        description="Carry between fairways, allocate berths, and answer a captain's requests")
    parser.add_argument("--once", action="store_true", help="one pass, rather than the loop")
    parser.add_argument("--interval", type=float, default=HEARTBEAT, help="seconds between passes")
    parser.add_argument("--no-fetch", action="store_true", help="do not reach the forge for other machines")
    parsed = parser.parse_args(argv)
    while True:
        if not parsed.no_fetch:
            fetch()
        count = once()
        if count:
            print(f"harbourmaster: {count} line(s) carried to {logs.HARBOUR}")
        if parsed.once:
            return 0
        time.sleep(parsed.interval)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
