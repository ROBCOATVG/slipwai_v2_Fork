"""The section of `commands/sail.md` that applies the model table, and the command that edits it.

Split from `stage_models.py`, which holds the table itself: that module is a declaration — one row per
stage, its role and what a delegate of it may touch — and this one is the English a project reads about it.
They parted at the budget, and the seam was already there in the first line of the other's docstring.

Nothing here decides anything. Every scope, type name and stage in this prose is rendered from `STAGES`,
so a stage that changes what its delegate may do changes these pages and cannot fail to.
"""
from __future__ import annotations

from ..layout import AT_ROOT, Layout
from .stage_models import (
    ANY,
    MANIFEST,
    NONE,
    READ_ONLY,
    REPORT,
    STAGES,
    TASK_COMMAND,
    TASKS,
)

# What each type may write and run, said in the sail section the way `agents/` declares it, so the ladder and
# the files cannot disagree about which delegate is allowed what.
SCOPE = {
    NONE: "nothing",
    MANIFEST: "the files its manifest names",
    REPORT: "only the report it produces",
    TASKS: "only the slice's `tasks.md`",
    READ_ONLY: "anything that reads",
    TASK_COMMAND: "anything that reads, plus the installed tasks command",
    ANY: "anything",
}


def delegable_types() -> str:
    """The table of types in the sail section: one row per delegable stage, from the declaration itself."""
    rows = "\n".join(
        f"| `{stage.key}` | `{stage.agent}` | {SCOPE[writes]} | {SCOPE[commands]} |"
        for stage in STAGES
        for writes, commands in [(stage.writes, stage.commands)]
        if writes is not None and commands is not None
    )
    return f"""| Stage | Type | Writes | Runs |
|---|---|---|---|
{rows}"""


def who_runs_each_stage(layout: Layout = AT_ROOT) -> str:
    """The `/sail` section that applies the table: read the line, delegate to the type, and say which ran."""
    types = delegable_types()
    return f"""## Who runs each stage

`.specify/models.json` says which model each stage runs on, by role: `strong` where a stage decides what to
build or whether it was built, `fast` where the input is already fully specified on paper — a plan into
tasks, `examples.md` into tests and code, a mutation run. Before running a stage, read its line:

```sh
python3 scripts/agents/models.py implement   # keyed by the command the stage runs; `{layout.make} models` prints them all
```

The line chooses the model; it does not require that model to inherit this session's context. Prefer a fresh
sub-agent whenever the stage can get all of its inputs from artifacts on disk. Six stages are exactly that,
and each is a **named agent type** this project carries in `agents/`, projected into the installed harness by
`{layout.make} agents` with its model and as much of its scope as that harness can enforce:

{types}

Every stage in that table is named for its purpose and then for the crew member who runs it, and every
stage that is not in it is named for the work alone — so the key says whether a stage has a delegate at all.
The gaps rung runs twice and only the pass after implementation is delegated: the pre-planning one may have
to ask a product question, which is the whole reason a stage stays here. Any other conversational stage stays
here too, and has no type for that reason. There is one more type, `sail-slice-watch`, for a whole slice
rather than a stage: *Running ready slices concurrently* is where it is delegated, and it reads this section
from inside its own worktree to choose a model for each stage it then runs. The last three rows,
`decide-skipper`, `demo-hand` and `unblock-bosun`, are `/cruise`'s: the product owner, the actor and the one
who gets a blocked run moving, delegated only when that command is running this ladder on its own
(`commands/cruise.md`). Under `/sail` alone they run nothing; a person is the owner and the actor.

Delegate to the type by name. The type is the standing brief, so the call adds only the task, its contract and
the file manifest — it never describes the role again or restates the scope, and it does not give the delegate
conclusions. It may give it a map: which precedent to copy, which decision in `research.md` governs, which
helper already exists — a file and a section, which the delegate then opens and reads for itself. Naming where
a fact lives is a pointer and costs a sentence; asserting what it says is a conclusion, and a brief that asked
the delegate to read a decision itself and report what it says has caught what a brief that summarised it got
wrong. Where a brief offers a delegate more than one way of working, every permission is written into each
mode that has it, even at the price of a repeated paragraph: a fresh delegate reads a silence conservatively,
and the conservative reading is the expensive one. The page each type is written on is `docs/delegated-agent-safety.md`, the standing boundary every
delegation is held to: reference it, restate none of it (`AGENTS.md`, *Delegated agents*).

**A delegate does not inherit this session's code-index connection, and needs none.** Where `AGENTS.md`
carries a code index's extension block, three of the types above — `sail-converge-navigator`, `sail-gaps-lookout` and
`sail-adversary-privateer` — are exploration-heavy, and *what does this code not yet do* is a blast-radius question the
index answers. Delegate them as the table says: a delegate reaches the index by the routes that block names,
which are the shell's and the harness's rather than this session's, so its brief's first route is one it has.
It names the route that answered, and falls back to text search only when the index says there is none. Never
pass the parent conversation merely to carry the connection.

Delegate both when the line names another model and when the same strong model can run in a fresh context.
On a harness whose agent file names a model (`scripts/agents/registry.json`, `agentFile`) the type already
carries the one the table resolved; everywhere else set it explicitly through the mechanism the registry
names, and never accept that mechanism's implicit default. If the harness cannot start a fresh sub-agent on
the selected model, run the stage here and say why. Then read its result from disk the way every stage is
read. Either way the stage says, in one line, which type ran it, which model, whether it was delegated and
whether its context was fresh (`sail-implement-shipwright · model: sonnet · delegated, fresh context` ·
`sail-adversary-privateer · model: host · delegated, fresh context` · `model: host, current context — harness cannot
delegate`). Those lines make type, model and context measurable; a stage that switched any of them silently
cannot be compared with one that did not. Nothing about what a stage produces changes with who runs it — the
artifacts, gates and stops are the same — and a sub-agent that meets a product decision hands the
question back here rather than answering it.

A stage is not always one delegate. Before delegating implementation, read `tasks.md` for its `[P]` markers and
its *Parallel opportunities* section: the tasks command writes both, and they are the plan for what may run
alongside what — written by one half of this workflow to be read here, not decoration. Every unchecked `[P]`
task whose files are disjoint from the batch already running is a concurrent sibling, delegated in the same turn
with a manifest of its own — and so is a task with no marker whose manifest shares no file with the batch. The
marker is the tasks command's reading of production-code contention, and it under-reports: one slice's list
marked one pair concurrent, said of the rest "none, by construction", and left two pairs that shared no file
to run in sequence. The manifests are the artifact; read them, and let only an overlap with a running
sibling's files, or what the section rules out, keep a task waiting. How many rules one delegate is handed
— a task, a rule or a user story — and how many RED tests each cycle opens with are `.specify/sail.json`'s
two settings (*How implementation is delegated* below), said in the stage line and put on the record. What the
section rules out stays sequential whatever the markers seem to allow — a RED-GREEN-REFACTOR increment starts
from a green, committed suite, and two of them at once is the batched-tests anti-pattern with a `[P]` on it.
The siblings are `sail-implement-shipwright` delegates, and that type is where the rule they cannot infer for
themselves already lives: **no concurrent delegate writes `tasks.md`**. It is the one file every sibling would
otherwise contend for, so each reports which task it finished and this session ticks the checkbox.

When several delegates form one batch, report once when the batch completes rather than once per delegate.
Verify their claims by spot-checking the recorded reproduction or RED evidence; do not repeat each complete
investigation in the host context. Do not re-investigate. A delegate that was stopped has filed nothing:
everything in its stop notification is a lead, never a result, and a lead is re-run before it is written
anywhere outside this session. An adversary pass is the same kind of batch:
disjoint-manifest seams of one pass are concurrent `sail-adversary-privateer` siblings in one turn, and the host
writes the log after the batch rather than re-attacking. It records the type and the explicit model that
ran each seam in `specs/<feature>/adversary-log.md`, especially when seams use different models.

The table is the project owner's to change at any point, and it is read before every stage rather than once,
so a change takes effect at the next stage — and rewrites the agent types, which carry the model on every
harness that reads one from a file: `/model-delegation-settings implement=strong claude.fast=haiku` edits it checked
(`commands/model-delegation-settings.md`, over `python3 scripts/agents/models.py --set`), or edit the file by hand and let
`make check-agents` hold the shape. When the owner asks for a different model at a stage, `/model-delegation-settings` is the
change — not a note, and not a switch made silently in the delegation. Commit the file: the choice is versioned with the project, and `slipwai
migrate` merges a newer factory's table over it rather than replacing it.
"""


def stage_keys() -> str:
    """Every stage key, in ladder order, for a page that must not keep its own list of them."""
    return ", ".join(f"`{stage.key}`" for stage in STAGES)


def model_delegation_settings_command(layout: Layout = AT_ROOT) -> str:
    """`/model-delegation-settings`: the table shown, or changed through the checked `--set` — never by editing a delegation."""
    keys = stage_keys()
    return f"""---
description: Show or change which model runs each stage of /sail
argument-hint: [stage=role | harness.role=identifier ...]
---

# Model delegation settings

`.specify/models.json` says which model runs each stage of `/sail`'s ladder, by role — `strong` where a
stage decides what to build or whether it was built, `fast` where the input is already fully specified on
paper — and what each role maps to on the harness this project is initialised for. This command is how the
table is read and how it changes: as and when, in one step, checked, and never by quietly picking a different
model inside a delegation.

## No argument — show the table

```sh
python3 scripts/agents/models.py
```

Report it as printed: the installed harness, whether it can choose a model for a sub-task at all and how
(`scripts/agents/registry.json`, `subagentModel`), then each stage's role, the model or the host model, and
why. No harness installed is a line of its own — `./init --integration <agent>` records one.

## Arguments — change it

Each argument is one of two edits, and the first thing to decide is which one the person means:

- `stage=role` moves a stage between roles — `implement-shipwright=strong` puts implementation back on the
  model running `/sail`. The keys are the stages: {keys}, and `default` for any stage without a row of its
  own. A stage whose key ends in a crew member's name is one with a delegate; the rest run on the host. A
  stage's name before the rename — `implement` for `implement-shipwright` — is still accepted and resolved.
- `harness.role=identifier` changes what a role runs on — `claude.fast=haiku`, or `claude.skipper=opus` to
  put a bigger model on `/cruise`'s product decisions than on driving. `host` is the model running `/sail`;
  `null` is no identifier mapped, which the line before each stage then says.

Pass them through exactly as given:

```sh
python3 scripts/agents/models.py --set $ARGUMENTS
```

It rewrites the agent types as it goes: `agents/sail-<stage>.md` is projected into the installed harness
with the model this table resolves, so a change here that left them behind would take effect on one harness
and not another, and `make check-agents` would report drift in a file nobody edited. The line saying so is
part of the output; report it.

The script refuses a stage the ladder does not have, a harness the registry does not know or records no
mechanism for, and any change that would leave the table malformed — and writes nothing then. Report a refusal
in its words; do not work around it by editing the file. A role a stage newly names is added as `null` under
every harness: say so, and ask for the identifier rather than inventing one.

Then show the line for each stage the change touches (`python3 scripts/agents/models.py implement`) and commit
`.specify/models.json` on its own, with a message naming the change. The choice is versioned with the project,
and a change buried in a slice's commit is a change nobody finds.

## When the request is in words

"Use the cheap model for implementation" is two possible edits, and the identifier is the part not to guess.
Where the harness's mechanism takes an alias the registry names (`identifiers` under its `subagentModel`), use
that spelling; otherwise ask which identifier, since model names are provider-specific and go stale. Never map
a role for a harness this project is not initialised for, and never for one the registry says cannot switch —
the script refuses the second, and the first is a setting nothing reads. A change takes effect at the next
stage `/sail` runs; nothing already running is interrupted. `{layout.make} models` prints the same table.
"""
