#!/usr/bin/env python3
"""Running an extension's guard before a tool call, and carrying a refusal back to the agent.

The sibling of `hooks.py`, and the differences are the point.

A hook runs around a rung and **is never fatal to it**: it is reported and the rung completes, because an
extension that could fail a stage can stop a delivery loop it was added to help. A guard runs in front of
one tool call and **may refuse that call**, by exiting 2 — and what it printed goes back to the agent, which
then does something else. The rung completes either way. No guard can end one.

    python3 scripts/extensions/guards.py before-search --query "def place_order" --stage implement

Exit 0: nothing refused, the call goes ahead. Exit 2: refused, and stderr is the reason the agent is given.
Anything a guard does other than exit 2 — a crash, a timeout, a non-zero code that is not 2 — is a hook's
behaviour: said on stderr, and the call goes ahead. A guard that cannot run is not a reason a delegate
cannot search.

`--elect <key>...` writes `.slipwai/guards.json`, and takes only the keys a person agreed to. An extension
is *elected* by being installed and *agreed to* by answering a question, because a guard refuses things a
person asked for. An extension that declares a guard nobody agreed to fires none.

`--offer <key>...` is that question, asked once by `./init` over the elected extensions: it says what each
one would be able to refuse and in whose words, then elects the ones agreed to. It reads and writes
`/dev/tty` rather than stdin and stdout, so a scripted or CI `./init` is not asked and agrees to nothing —
silence is *no*, which is the only safe direction for a question about refusing somebody's tool calls.

Standalone and dependency-free: this ships inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AVAILABLE = HERE / "available-guards.json"
#: Shorter than a hook's 30s: this is in front of a tool call somebody is waiting on.
DEFAULT_BUDGET = "5s"
#: The exit code that refuses. Every other one is a hook's behaviour.
REFUSE = 2


def project_root() -> Path:
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


ROOT = project_root()
REGISTRY = ROOT / ".slipwai/guards.json"


def seconds(budget: str) -> float:
    """A budget as seconds. A budget nobody can parse is not a reason a guard does not run."""
    text = str(budget).strip().lower()
    scale = {"s": 1.0, "m": 60.0, "h": 3600.0}.get(text[-1:], 1.0)
    try:
        return float(text.rstrip("smh")) * scale
    except ValueError:
        return 5.0


def read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}


def elect(keys: list[str]) -> int:
    """Write `.slipwai/guards.json` for the extensions `keys` names — the ones a person agreed to."""
    available = read(AVAILABLE)
    guards: dict[str, list[dict]] = {}
    for key in sorted(set(keys)):
        for name, body in sorted(available.get(key, {}).items()):
            guards.setdefault(name, []).append({"extension": key, **body})
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps({"v": 1, "guards": guards}, indent=2) + "\n", encoding="utf-8")
    attached = ", ".join(sorted(guards)) or "no guard"
    print(f"guards: {len(set(keys) & set(available))} extension(s) may refuse at {attached}")
    return 0


#: What each guard can stop, in the words a person deciding needs. The keel's `guards.py` is where these
#: are written; this is the copy a project reads, because there is no keel in a project to ask.
REFUSING = {
    "session": "stop a delegate's session before its first tool call",
    "before-search": "stop a search of the tree and tell the agent what to ask instead",
    "after-delegate": "reject a delegate's answer and have it asked again",
}


def offer(keys: list[str]) -> int:
    """Ask once whether the elected extensions may refuse tool calls, then elect the ones agreed to.

    Over `/dev/tty`, so a scripted or CI `./init` is never asked — and agrees to nothing. A question about
    whether software may refuse what a person told it to do has one safe answer when nobody is there.
    """
    available = read(AVAILABLE)
    offered = {key: available.get(key, {}) for key in sorted(set(keys)) if available.get(key)}
    if not offered:
        return elect([])
    try:
        with open("/dev/tty", "r+", encoding="utf-8") as tty:
            tty.write("\nThese extensions can refuse a tool call:\n")
            for key, declared in offered.items():
                for name in sorted(declared):
                    tty.write(f"  {key}: {REFUSING.get(name, name)}\n")
            tty.write("A guard never ends a stage — it stops one call and tells the agent why.\n")
            tty.write("Allow them? [y/N]: ")
            tty.flush()
            answer = tty.readline().strip().lower()
    except OSError:
        print("guards: nothing asked and nothing allowed — `./init` was not run from a terminal; "
              "`python3 scripts/extensions/guards.py --elect <keys>` allows them later", file=sys.stderr)
        return elect([])
    return elect(list(offered) if answer in ("y", "yes") else [])


def applies(body: dict, given: dict[str, str]) -> bool:
    """Whether this guard wants this rung. One that names no `stages` wants all of them."""
    stages = body.get("stages")
    return not isinstance(stages, list) or given.get("stage") in stages


def reason(run: subprocess.CompletedProcess) -> str:
    """What the agent is told. Everything the guard wrote, not just its last line — a refusal that says
    *ask the index instead, like this* is only useful whole, and this is the one place an extension gets to
    say something to the model rather than to a log."""
    said = ((run.stderr or "") + (run.stdout or "")).strip()
    return said or "refused, and said nothing about why"


def fire(name: str, given: dict[str, str]) -> int:
    """Run every guard on `name`. 2 as soon as one refuses; 0 otherwise.

    In extension-name order and stopping at the first refusal, because the call is already not happening and
    a second opinion about a call nobody is making is noise a person has to read.
    """
    for body in read(REGISTRY).get("guards", {}).get(name, []):
        key, script = body.get("extension", "?"), body.get("run", "")
        if not applies(body, given):
            continue
        path = ROOT / "scripts/extensions" / key / script
        if not path.is_file():
            print(f"guard {key} {name}: {path} is not in this project", file=sys.stderr)
            continue
        environment = {**os.environ, **{f"SLIPWAI_{word.upper()}": value for word, value in given.items()}}
        try:
            run = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, cwd=ROOT,
                                 timeout=seconds(body.get("budget", DEFAULT_BUDGET)), env=environment)
        except subprocess.TimeoutExpired:
            # Not a refusal. A guard that ran out of time has said nothing, and a tool call stopped by
            # silence is a delegate blocked by a bug in something it was never told about.
            print(f"guard {key} {name}: over its {body.get('budget', DEFAULT_BUDGET)} budget, ended; the "
                  f"call goes ahead", file=sys.stderr)
            continue
        except OSError as error:
            print(f"guard {key} {name}: could not run ({type(error).__name__}); the call goes ahead",
                  file=sys.stderr)
            continue
        if run.returncode == REFUSE:
            print(reason(run), file=sys.stderr)
            return REFUSE
        if run.returncode != 0:
            print(f"guard {key} {name}: exited {run.returncode}, which is not a refusal; the call goes "
                  f"ahead", file=sys.stderr)
            continue
        if run.stdout.strip():
            print(run.stdout.strip())
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 0
    if argv[0] == "--elect":
        return elect(argv[1:])
    if argv[0] == "--offer":
        return offer(argv[1:])
    given: dict[str, str] = {}
    rest = argv[1:]
    for index in range(0, len(rest) - 1, 2):
        if rest[index].startswith("--"):
            given[rest[index][2:]] = rest[index + 1]
    return fire(argv[0], given)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
