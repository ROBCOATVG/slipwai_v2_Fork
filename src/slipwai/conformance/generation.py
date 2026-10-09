"""The `profiles` and `targets` checks: generate each backend the way a project maker would, and read what it needs.

A profile is answered when `slipwai generate --profile <p> --skip-checks` succeeds for the backend; where the profile
asks where events live, the backend must also offer an event store and answer its files, because generation skips a
feature the layout lacks and would pass with no store at all. Every profile is generated under the
backend's first target, and the richest profile once under every target it declares, with the event store that
target provisions where it offers one, so a backend with four targets costs five generations. `--frontend none`:
the suite checks a language, not a browser app.
"""
from __future__ import annotations

import re
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

from ..catalog import CATALOG, axis_options
from ..images import POSTGRES_SSLMODE_KINDS
from ..project.flag_route import OPT_IN_TRANSPORT
from ..registry import OPT_IN_FLAG_TRANSPORTS, POSTGRES_SSLMODE, READ_SIDE_FILES, WRITE_SIDE_FILES, Registry
from . import child

EVENT_STORE = "persistence"
# How `slipwai` names the package a refusal is about: the finding names the backend already, so it is said once.
REFUSED = re.compile(r"^slipwai: language \S+ \(.*?\): ")
PROJECT = "conformance"


@dataclass(frozen=True)
class Run:
    """One generation: what was asked, and the project it wrote or the last line `generate` said instead."""

    backend: str
    profile: str
    target: str
    choices: tuple[tuple[str, str], ...]
    project: Path | None
    said: str


def targets_of(key: str) -> list[str]:
    """The targets the backend's own row declares, in its order: the loaded backend's row, so it is always there."""
    return list(CATALOG["backends"][key]["targets"])


def richest() -> str:
    """The profile of the highest tier: the one every target is generated under."""
    return max(CATALOG["profiles"], key=lambda name: CATALOG["profiles"][name].get("tier", 0))


def provisioned(backend: str, target: str) -> tuple[tuple[str, str], ...]:
    """The event store `target` provisions, as a choice, where the backend is offered one there; else the default."""
    for option in axis_options(EVENT_STORE, backend, target):
        if CATALOG["axes"][EVENT_STORE]["options"][option].get(target, {}).get("provisions"):
            return ((EVENT_STORE, option),)
    return ()


def generate(output: Path, backend: str, profile: str, target: str, choices: tuple[tuple[str, str], ...]) -> Run:
    """`slipwai generate` in a process of its own, as a project maker runs it, into a directory of its own."""
    parent = output / str(len(list(output.iterdir())))
    parent.mkdir()
    arguments = ["generate", PROJECT, "--profile", profile, "--backend", backend,
                 "--frontend", "none", "--target", target, "--output", str(parent), "--skip-checks"]
    for axis, option in choices:
        arguments += [f"--{axis}", option]
    done = child.run("slipwai", arguments)
    if done.returncode == 0 and (parent / PROJECT).is_dir():
        return Run(backend, profile, target, choices, parent / PROJECT, "")
    if done.returncode == 0:  # an exit the package forced, `os._exit(0)` included, writes nothing
        return Run(backend, profile, target, choices, None, "exit 0 with no project written")
    said = REFUSED.sub("", done.last_line(), count=1)
    return Run(backend, profile, target, choices, None, said or f"exit {done.returncode}")


def runs(output: Path, backend: str) -> list[Run]:
    """Every generation the two checks read for one backend: each profile at its first target, then the richest
    profile at each other target it declares."""
    targets = targets_of(backend)
    top = richest()
    plan = [(profile, targets[0], provisioned(backend, targets[0]) if profile == top else ())
            for profile in CATALOG["profiles"]]
    plan += [(top, target, provisioned(backend, target)) for target in targets[1:]]
    return [generate(output, backend, profile, target, choices) for profile, target, choices in plan]


def event_store_findings(loaded: Registry, backend: str) -> list[str]:
    """Where a profile asks where events live: an event store offered, and every one offered answered with files."""
    axis = CATALOG["axes"][EVENT_STORE]
    targets = targets_of(backend)
    offered = list(dict.fromkeys(option for target in targets for option in axis_options(EVENT_STORE, backend, target)))
    if not offered:
        return [f"backend {backend} offers no event store, so it does not answer {profile} (FR-031)"
                for profile in CATALOG["profiles"] if profile in axis["profiles"]]
    findings: list[str] = []
    for option in offered:
        for feature in dict.fromkeys([*axis["options"][option]["features"], *axis["always"]]):
            for member in (WRITE_SIDE_FILES, READ_SIDE_FILES):
                if feature not in loaded.answer(backend, member):
                    findings.append(f"backend {backend} offers event store {option}, and {member.name} answers "
                                    f"nothing for {feature}")
    return list(dict.fromkeys(findings))


def stopped(run: Run, named: Collection[str]) -> bool:
    """Whether the run stopped on a fault another check already named: a line of `named` in what it said."""
    return run.project is None and any(line in run.said for line in named)


def failed(run: Run, named: Collection[str]) -> bool:
    """Whether the run did not generate for a cause of its own: one that `stopped` is that check's finding, shown
    once there and not again per run."""
    return run.project is None and not stopped(run, named)


def read_by(backend: str, done: list[Run]) -> dict[str, list[Run]]:
    """The runs each check reads: `profiles` every profile at the first target, `targets` the richest profile at
    each target, `prune rows` all of them."""
    first, top = targets_of(backend)[0], richest()
    return {"profiles": [run for run in done if run.target == first],
            "targets": [run for run in done if run.profile == top],
            "prune rows": list(done)}


def profile_findings(loaded: Registry, backend: str, done: list[Run], named: Collection[str] = ()) -> list[str]:
    first = targets_of(backend)[0]
    findings = [f"backend {backend} does not generate under {run.profile}: {run.said}"
                for run in done if run.target == first and failed(run, named)]
    return findings + event_store_findings(loaded, backend)


def target_findings(loaded: Registry, backend: str, done: list[Run], named: Collection[str] = ()) -> list[str]:
    """Each declared target generated once, and the members keyed by what a target provisions read for it."""
    first = targets_of(backend)[0]
    findings = [f"backend {backend} does not generate for target {run.target}: {run.said}"
                for run in done if run.target != first and failed(run, named)]
    modes = loaded.answer(backend, POSTGRES_SSLMODE)
    for run in done:
        for axis, option in run.choices:
            kind = CATALOG["axes"][axis]["options"][option].get(run.target, {}).get("provisions")
            if kind in POSTGRES_SSLMODE_KINDS and (not isinstance(modes, dict) or kind not in modes):
                findings.append(f"backend {backend} answers postgres_sslmode with no {kind}, which {run.target} "
                                f"provisions {option} as")
    findings += [f"backend {backend} names {target} in opt_in_flag_transports, which has no opt-in flag transport"
                 for target in sorted(loaded.answer(backend, OPT_IN_FLAG_TRANSPORTS)) if target not in OPT_IN_TRANSPORT]
    return list(dict.fromkeys(findings))
