"""The second closed set: the moments an extension may *refuse* something, and the three of them.

`hooks.py` is the first set, and its second rule is the reason this file exists: **a hook is never fatal to
the rung.** It is reported and the rung completes, because an extension that could fail a stage is an
extension that can stop a delivery loop it was added to help.

That rule left one thing unbuildable. `codegraph` wants to say *don't grep for that, ask the index* — which
is not a report after the fact, it is an answer to a tool call that has not happened yet. Version 1 reached
it through Claude Code's own `PreToolUse` hook, so it worked on one harness and silently did nothing on the
rest. Widening `hooks` to allow a refusal would have made every hook able to fail a rung, which is the
control plane the rule is there to prevent.

**So a guard is its own kind.** Three differences from a hook, and they are the whole design:

1. **A guard fires before a tool call, not around a rung.** What it can stop is that one call.
2. **A guard may refuse, by exiting 2.** The reason it printed goes back to the agent, which then does
   something else — usually the thing the guard suggested. Every other exit code is a hook's behaviour:
   reported, and the call goes ahead.
3. **The rung completes either way.** A refused tool call is not a failed stage. `hooks.py`'s rule is about
   rungs and it is untouched: no guard can end one.

The shape is the harnesses' own: Claude Code, Codex and Cursor all have a pre-tool event where a non-zero
exit blocks the call and the message reaches the model. This is the keel's name for that, so an extension
declares it once instead of once per harness.

**A guard is agreed to, not installed.** A hook runs where an extension is elected; a guard also refuses
things a person asked for, so election names the guards an extension declares and takes the person's word
once. An extension that declares a guard nobody agreed to fires none — `.slipwai/guards.json` is written
from the agreement, not from the manifest, and like `.slipwai/hooks.json` it is a controlled file.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Where the resolved registry is written. A controlled file, for the same reason the hook registry is: a
#: run that could register a guard on itself could also unregister one.
REGISTRY = ".slipwai/guards.json"
#: What an extension's manifest declares its guards under.
BLOCK = "guards"
#: How long one guard may take before it is ended, where its declaration does not say. Shorter than a
#: hook's: this one is in front of a tool call, and a tool call a person is waiting on cannot wait 30s.
DEFAULT_BUDGET = "5s"
#: The exit code that refuses the call. Every other code is a hook's behaviour — said, and the call goes on.
REFUSE = 2


@dataclass(frozen=True)
class Guard:
    """One moment a tool call may be refused, what the guard is handed, and what refusing it does."""

    name: str
    when: str
    given: tuple[str, ...]
    refusing: str


#: In firing order. `session` is first because it is the only one that is not about a single tool call.
GUARDS: tuple[Guard, ...] = (
    Guard("session", "a delegate's session opens, before its first tool call",
          ("stage", "slice", "fairway", "berth"),
          "the session does not start, and the stage is dispatched again without this extension's guard"),
    Guard("before-search", "a delegate is about to search the tree — grep, find, a file read by glob",
          ("stage", "slice", "fairway", "query", "tool"),
          "that search does not run, and the agent is told what to ask instead"),
    Guard("after-delegate", "a delegate has answered, before its answer is used",
          ("stage", "slice", "fairway", "tool"),
          "the answer is not used, and the agent is told why and asked again"),
)
NAMES = tuple(guard.name for guard in GUARDS)


def guard(name: str) -> Guard:
    """One guard by name, or a refusal listing the set.

    Refused rather than ignored, exactly as a hook point is: an extension that declared a guard the keel has
    not got would be installed, valid, and silently never run — the failure that is hardest to notice.
    """
    for declared_guard in GUARDS:
        if declared_guard.name == name:
            return declared_guard
    raise KeyError(f"`{name}` is not a guard the keel fires. There are {len(GUARDS)}, in firing order: "
                   f"{', '.join(NAMES)}. A guard may refuse a tool call; a hook never can, and the two sets "
                   f"are separate for that reason")


def declared(manifest: dict) -> dict[str, dict]:
    """An extension's guards, normalised. The short and the long form read the same, as a hook's do."""
    block = manifest.get(BLOCK)
    if not isinstance(block, dict):
        return {}
    found: dict[str, dict] = {}
    for name, body in block.items():
        guard(name)
        if isinstance(body, str):
            found[name] = {"run": body, "budget": DEFAULT_BUDGET}
        elif isinstance(body, dict) and body.get("run"):
            found[name] = {"budget": DEFAULT_BUDGET, **body}
        else:
            raise ValueError(f"the `{name}` guard names no script to run. A guard is a path, or an object "
                             f"with `run` and optionally `stages` and `budget`")
    return found


def registry(manifests: dict[str, dict], agreed: set[str] | None = None) -> dict:
    """`.slipwai/guards.json`: every *agreed* extension's guards, by guard, in firing order.

    `agreed` is the set of extension keys a person has said yes to; None means none have been asked, which
    writes an empty registry rather than every manifest's guards. An extension is elected by installing it
    and agreed to by answering a question, and those are deliberately two things.
    """
    allowed = set() if agreed is None else agreed
    by_guard: dict[str, list[dict]] = {name: [] for name in NAMES}
    for extension in sorted(manifests):
        if extension not in allowed:
            continue
        for name, body in sorted(declared(manifests[extension]).items()):
            by_guard[name].append({"extension": extension, **body})
    return {"v": 1, "guards": {name: by_guard[name] for name in NAMES if by_guard[name]}}
