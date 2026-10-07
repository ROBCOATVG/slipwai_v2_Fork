#!/usr/bin/env python3
"""Casting off: start the harbourmaster and one captain per fairway, and get out of the way.

`cruise.py` was a runner. It held the state of the run, decided what happened next, and died at iteration
two — after which seventeen iterations ran from interactive sessions and it knew about none of them. The
replacement is not a better runner. It is **no runner**: the state lives in the logs, the captains read them,
and the thing you type starts processes and exits.

That is the whole of this file, and the shortness is the point. Nothing here is in the loop, so nothing here
can be the thing that died.

**One captain per fairway the chart names**, under the telegraph's position — `boilers` is how many may be
lit at once, so the rest wait for a berth rather than all starting and competing for one machine.

**Started detached, and recorded by their pid files.** `--stop` reads them back. A process this started that
is no longer running is said rather than cleaned up quietly: a captain that exited is a fact, and `stop`
pretending it tidied something is how a person stops believing the output.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import clearance  # noqa: E402


def project_root() -> Path:
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


ROOT = project_root()
RUNNING = ROOT / ".slipwai/running"
HARBOUR_CONFIG = ROOT / "harbour.json"


def config() -> dict:
    try:
        held = json.loads(HARBOUR_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) else {}


def fairways() -> list[str]:
    """Every fairway the chart names, in its own order, which is split order."""
    charted, _ = clearance.chart()
    found: list[str] = []
    for body in (charted.get("slices") or {}).values():
        name = str((body or {}).get("fairway", "")) if isinstance(body, dict) else ""
        if name and name not in found:
            found.append(name)
    return found


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def recorded() -> dict[str, int]:
    """What was started last time, from the pid files, whether or not it is still running."""
    found: dict[str, int] = {}
    for path in sorted(RUNNING.glob("*.pid")) if RUNNING.is_dir() else []:
        try:
            found[path.stem] = int(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
    return found


def start(name: str, argv: list[str]) -> int:
    """One process, detached, with its own log, and its pid written down."""
    RUNNING.mkdir(parents=True, exist_ok=True)
    out = (RUNNING / f"{name}.out").open("a", encoding="utf-8")
    process = subprocess.Popen(argv, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT,
                               start_new_session=True)
    (RUNNING / f"{name}.pid").write_text(f"{process.pid}\n", encoding="utf-8")
    return process.pid


def cast_off(limit: int | None) -> int:
    """Start the harbourmaster and up to `limit` captains. Returns how many processes were started."""
    standing = {name: pid for name, pid in recorded().items() if alive(pid)}
    started = 0
    if "harbourmaster" not in standing:
        pid = start("harbourmaster", [sys.executable, str(HERE / "harbourmaster.py")])
        print(f"harbourmaster started, pid {pid}")
        started += 1
    else:
        print(f"harbourmaster already running, pid {standing['harbourmaster']}")
    lit = len([name for name in standing if name != "harbourmaster"])
    for fairway in fairways():
        name = f"captain-{fairway}"
        if name in standing:
            print(f"{fairway}: captain already running, pid {standing[name]}")
            continue
        if limit is not None and lit >= limit:
            print(f"{fairway}: waiting for a berth — the telegraph lights {limit} at once")
            continue
        pid = start(name, [sys.executable, str(HERE / "captain.py"), fairway])
        print(f"{fairway}: captain started, pid {pid}")
        started, lit = started + 1, lit + 1
    return started


def stop_all() -> int:
    """Ask every process this started to stop, and say which were already gone."""
    stopped = 0
    for name, pid in recorded().items():
        if not alive(pid):
            print(f"{name}: not running (pid {pid} is gone)")
            (RUNNING / f"{name}.pid").unlink(missing_ok=True)
            continue
        os.kill(pid, signal.SIGTERM)
        print(f"{name}: asked to stop (pid {pid}). A captain stops at its next boundary")
        stopped += 1
    return stopped


def listing() -> list[str]:
    """What is running, and what was started and is not. `slipwai fleet` is where the work is shown; this
    is only about the processes, which is a different question and one `fleet` deliberately does not ask."""
    found = recorded()
    if not found:
        return ["nothing has been started here"]
    return [f"  {name:<22} pid {pid:<8} {'running' if alive(pid) else 'gone'}"
            for name, pid in sorted(found.items())]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="fleet", description="Start the harbourmaster and a captain per fairway, and exit",
        epilog="This is not a runner. The state of the run is in the logs, the captains read them, and this "
               "starts processes and gets out of the way — so nothing here can be the thing that died.")
    parser.add_argument("verb", nargs="?", choices=("start", "stop", "list"), default="start")
    parser.add_argument("--boilers", type=int, default=None,
                        help="how many captains may run at once (default: the telegraph's)")
    parsed = parser.parse_args(argv)
    if parsed.verb == "stop":
        stop_all()
        return 0
    if parsed.verb == "list":
        print("\n".join(listing()))
        return 0
    held = config()
    limit = parsed.boilers if parsed.boilers is not None else held.get("boilers")
    if isinstance(limit, int) and limit <= 0:
        print(f"the telegraph is at {held.get('position', 'stop')}, which lights no captains. "
              f"`slipwai telegraph half-ahead` casts off again")
        return 0
    cast_off(limit if isinstance(limit, int) else None)
    print("`slipwai fleet` shows what they are doing; `slipwai bridge` is the page you answer from")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
