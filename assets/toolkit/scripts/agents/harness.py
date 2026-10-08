#!/usr/bin/env python3
"""Which coding agent a headless session runs through, and the command that starts one.

Two things in this directory need to start a fresh harness session and ask it one thing: `cruise.py`, which
asks `/cruise` once an iteration, and `captain.py`, which asks `/drive` once a slice. They had one copy
between them and it was `cruise.py`'s — so the captain, which is the thing that will outlive the runner,
fell back to `scripts/agents/drive.py`. That script is the *settings reader* for `/drive`: handed a slice
and a fairway it prints its table and exits 0. A whole real run was reported through on the strength of it.

So the knowledge is here, and both callers read it:

**Which harness.** The first harness `.specify/integration.json` records as installed that has a verified
`headless` row in `registry.json` and whose binary is on PATH. Not the first one on PATH: a harness `./init`
never initialised here has no projected commands, no delegate types and no hook files, so the command being
asked for is unknown to it and the session ends having done nothing. One that is on PATH but uninitialised
is *named in the refusal*, with the `./init` that would add it, rather than driven.

**What to ask it.** A harness whose row says its print mode resolves this project's slash commands
(`prompt: "slash"`) is asked `/<command>`; every other is asked to read the command file and follow it,
which needs nothing of a harness beyond reading a file and is the same words whatever the harness.

**What the session must not inherit.** A harness session started from inside another's reads the parent's
identity out of the environment and either takes the parent's transcript for its own or refuses to start as
a nested copy. Every harness's session variable comes out, and the row's own `env` goes in.

Nothing here decides anything about a run. It answers *how to start a session*, and the caller says what the
session is for. Standalone and dependency-free, like everything under `scripts/`.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "registry.json"


def project_root(script: Path, depth: int) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 2)
INTEGRATION = ROOT / ".specify/integration.json"
#: The environment a harness session started from inside another's must not inherit: the parent's own
#: identity, or the child reads the parent's transcript as its own and refuses to start as a nested copy.
PARENT_SESSION_VARIABLES = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")


class NoHarness(RuntimeError):
    """No harness here can be asked anything, said as the one line a person reads and acts on."""


def registry() -> dict[str, dict[str, Any]]:
    return {row["key"]: row for row in json.loads(REGISTRY.read_text(encoding="utf-8"))["harnesses"]}


def installed_keys() -> list[str]:
    """The harnesses Spec Kit recorded as installed here, in the order it recorded them; none where it never ran."""
    if not INTEGRATION.is_file():
        return []
    try:
        state = json.loads(INTEGRATION.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return []
    keys = state.get("installed_integrations") or [state.get("default_integration")]
    return [key for key in keys if isinstance(key, str)]


def headless_row(harness: dict[str, Any] | None) -> dict[str, Any] | None:
    row = harness.get("headless") if harness is not None else None
    return row if isinstance(row, dict) else None


def binary_of(harness: dict[str, Any]) -> str:
    """The executable a harness's headless command starts with: what is looked for on PATH."""
    row = headless_row(harness)
    assert row is not None
    return shlex.split(str(row["command"]))[0]


def choose() -> tuple[dict[str, Any], str]:
    """The harness a session runs through, and a sentence saying why that one, or `NoHarness` saying why none.

    The refusal is the whole value of this function. "No harness" has three different causes and three
    different things a person does about them — one is installed and its binary is missing, one is installed
    and the registry records no way to run it headless, or one is on PATH and was never initialised here —
    and a run that said only "no harness" would send them to read source to tell which.
    """
    rows = registry()
    installed = [key for key in installed_keys() if key in rows]
    for key in installed:
        harness = rows[key]
        if headless_row(harness) is not None and shutil.which(binary_of(harness)):
            return harness, f"harness: {harness['name']}"
    on_path = [harness for key, harness in rows.items()
               if key not in installed and headless_row(harness) is not None and shutil.which(binary_of(harness))]
    able = ", ".join(f"{harness['name']} (`{binary_of(harness)}`)" for harness in rows.values()
                     if headless_row(harness) is not None)
    named = ", ".join(rows[key]["name"] for key in installed) or "no harness is initialised here"
    words = " is installed" if len(installed) == 1 else " are installed" if installed else ""
    if installed and headless_row(rows[installed[0]]) is None:
        words += ", and the registry records no way to run it headless"
    elif installed:
        words += f", and `{binary_of(rows[installed[0]])}` is not on PATH"
    if on_path:
        found = ", ".join(f"{harness['name']} (`./init --integration {harness['key']}`)" for harness in on_path)
        raise NoHarness(f"no initialised harness a session can run through is on PATH: {named}{words}. On "
                        f"PATH but never initialised here, so its commands, delegate types and hooks are "
                        f"not projected: {found} — that init adds it beside what is installed; then run "
                        f"again")
    raise NoHarness(f"no harness a session can run through is on PATH: {named}{words}, and none of the "
                    f"harnesses the registry records a headless command for is on PATH — {able} "
                    f"(scripts/agents/registry.json, `headless`)")


def template(harness: dict[str, Any], sandbox: bool = False) -> tuple[str, str]:
    """The shell template a session runs, and the sentence saying which permissions it runs under."""
    headless = headless_row(harness)
    assert headless is not None
    permissions = headless.get("sandboxPermissions" if sandbox else "permissions", "")
    why = ("--sandbox: every permission check is bypassed, which is only for a container with nothing to lose"
           if sandbox else
           "edits are accepted and every other permission is the harness's own to grant or refuse; pass "
           "--sandbox inside a disposable container to bypass them all")
    said = str(headless["command"]).replace("{permissions}", permissions)
    # A headless session in a checkout nobody has trusted ignores the project's own MCP file on some
    # harnesses, so the row's `headlessFlags` make it honoured — passed only when the file exists, since a
    # flag naming a missing file refuses to start, and `{root}` is this checkout for a harness that trusts
    # by path.
    project = harness.get("projectMcp")
    if isinstance(project, dict) and project.get("headlessFlags") and (ROOT / str(project["file"])).is_file():
        said = f"{said} {str(project['headlessFlags']).replace('{root}', str(ROOT))}"
    # The ladder's concurrent slices work in worktrees beside the checkout, which a print session under
    # `acceptEdits` is refused every edit in; the row's `worktreeFlags` name the directory the checkout sits
    # in as a second working directory, so a delegate's first edit is not its last.
    worktrees = headless.get("worktreeFlags")
    if worktrees:
        said = f"{said} {str(worktrees).replace('{parent}', shlex.quote(str(ROOT.parent)))}"
    return said, why


def model_flags(harness: dict[str, Any] | None, model: str | None) -> str:
    """What puts a session on a named model: the row's `modelFlag` with the identifier in it. Nothing where
    no model is named or where the row records no flag — the caller says which, because "the harness's own
    default ran" is a thing a reader has to be told rather than infer from a transcript."""
    headless = headless_row(harness)
    flag = headless.get("modelFlag") if headless is not None else None
    if not model or not flag:
        return ""
    return " " + str(flag).replace("{model}", shlex.quote(model))


def prompt_for(harness: dict[str, Any] | None, command: str, file: Path, argument: str | None = None) -> str:
    """What a session is asked: the slash command, or the words that make any harness read the file."""
    headless = headless_row(harness)
    if headless is not None and headless.get("prompt") == "slash":
        return f"/{command} {argument}" if argument else f"/{command}"
    where = file.relative_to(ROOT).as_posix() if file.is_relative_to(ROOT) else str(file)
    tail = f", with `{argument}` as its argument" if argument else "; it is given no argument"
    return f"Run the /{command} command: read {where} and follow it exactly as written{tail}."


def child_environment(harness: dict[str, Any] | None) -> dict[str, str]:
    """What a session runs under: this environment, plus what the row's `headless.env` sets — Claude Code's
    wait ceiling, which otherwise ends a print session while its delegates still run — and minus every
    harness's own session variables."""
    environment = dict(os.environ)
    for variable in PARENT_SESSION_VARIABLES:
        environment.pop(variable, None)
    for row in registry().values():
        session_variable = (row.get("usage") or {}).get("env")
        if session_variable:
            environment.pop(str(session_variable), None)
    headless = headless_row(harness)
    if headless is not None and isinstance(headless.get("env"), dict):
        environment.update({str(key): str(value) for key, value in headless["env"].items()})
    return environment
