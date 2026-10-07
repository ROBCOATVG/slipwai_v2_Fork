"""`commands/`: the workflow commands adapted to this project's profile and toolchain."""
from __future__ import annotations

from ..catalog import CATALOG
from ..layout import AT_ROOT, Layout
from ..origin import Adoption
from ..services import App, backends_of, web_apps
from ..targets import managed
from .add_commands import add_command_files
from .adversary import adversary_command
from .benchmark import benchmark_command, what_each_stage_costs
from .catch_up_command import catch_up_files
from .cruise import cruise_command, cruise_settings_command
from .cruise_seat import cruise_status_command, cruise_stop_command, cruise_tell_command, cruise_watch_command
from .demo_stop import demo_stop
from .drive_settings import drive_settings_command, implementation_section
from .flags import PUSH_CHECK
from .ladder import drive_ladder, hook_points
from .mutation import mutation_command
from .parallel_slices import concurrent_slices, done_marker, ready_set_selection
from .stage_models import model_delegation_settings_command, who_runs_each_stage
from .whats_next import whats_next_command
from .where_are_we import where_are_we_command


def drive_command(
    event: bool, apps: list[App], target: str = "none", layout: Layout = AT_ROOT, adoption: Adoption | None = None,
) -> str:
    resolution = "the requested slice in `docs/event-model/model.yaml`" if event else "the requested feature or the active directory recorded in `.specify/feature.json`"
    web = web_apps(apps)
    baseline = ", ".join(f"`{app.path}`" for app in web)
    ladder = drive_ladder(event, apps, target, layout, adoption)
    return f"""---
description: Drive one slice through planning, implementation, and an actor-visible demo
argument-hint: [slice-id-or-feature]
---

# Drive

Deliver one small vertical slice under `AGENTS.md`. Once the ladder below has produced it, resolve
{resolution}.

## Enter at the first incomplete stage

Read artifacts from disk rather than conversation memory and walk this ladder from the top. The entry stage
is the first one whose artifact is missing, empty, or still a placeholder — **including the stages upstream
of the slice loop**. State the entry stage and the evidence that selected it before changing anything, then
run that stage and every stage after it. Never rerun a completed stage merely to check. Where `.codegraph/` is in
the tree, a caller or blast-radius question is one index call — `scripts/codegraph callers <symbol>`, or
`codegraph_explore` — and not a text search; grep is for words in documents.

**The checkout goes stale the way conversation memory does, so check the branch before the artifacts.**
Every signal the ladder reads — a slice's `status`, whether `examples.md` or `tasks.md` exists, the slice
graph — is a property of this commit, and a branch behind trunk reads exactly like a project where the work
was never done: a `/drive` fifty-seven commits behind wrote a second example map for a slice that had
shipped. So fetch and compare first — `git fetch`, then `git log --oneline HEAD..@{{u}}`, or against
`origin/main` where the branch has no upstream. Behind by anything, stop and say so rather than deriving:
the artifacts about to be read are not the project's current ones. The evidence line names the branch, its
head and its distance from trunk in the same breath as the stage. Where the fetch could not run — no remote,
or a remote this environment cannot reach — the line says *could not verify this checkout is current*, and
that never reads as *current*.

{ladder}

Being invoked before any of this exists is a valid start, not an error: it means the entry stage is near the
top of the ladder. Step back to that stage and say so rather than reporting that the request came too early.
Never invent a principle, specification, event, command, stream, or slice to skip a stage — a missing
artifact is work to do with the user, not a gap to fill from context. A stage needing a real product
decision is a stop.

{who_runs_each_stage(layout)}
{what_each_stage_costs(layout)}
{implementation_section(layout)}
{hook_points()}
## Once inside the slice

Start the slice from a green `make verify`. During implementation, take one RED-GREEN-REFACTOR increment per
task — one rule of the example map with its examples, where the map numbers its rules — run only the quickest
relevant tests in the same file or area, commit that increment locally, and keep
task checkboxes truthful. A local commit is not a push: it does not run the full gate and it does not start
CI. Do not push increment commits until the hand's verdict on this slice's examples is green. Before an increment that changes a
shared function, ask `codegraph_explore` what calls it and what the change reaches — loaded by name where the
harness defers it — and name those callers in the delegate's manifest; a project without `.codegraph/` answers
with a text search and says so.

When the tasks are done, converge, then have the hand walk this slice's examples from the unpushed slice
branch and record its verdict. **Nobody is stopped here.** A person's demo is per capability and runs when
the capability's last slice has merged, which is usually several slices later; this rung proves the path
works, and the person is shown the whole thing rather than its instalments. After a green verdict — and only
then — a project that has adopted CodeGraph runs `codegraph sync`, then the full
`make verify`, then the first push of those increment commits (and the merge that lands them on trunk).
That push is the integration boundary. A claim of `slice/<id>` at the start of the slice may still push a
lock ref from `main`; that is not the implementation.

{demo_stop(event, baseline)}

### After the hand's verdict, and after Phase 4 clears

After a green verdict, run `/adversary`, which decides whether the slice changed attack surface or closed the
split and records the attack or the skip — `make check-decisions` holds every done slice to that row. Close the
adversary benchmark entry after its findings are triaged; implement confirmed defects through failing tests,
each in an `implement` entry. Then run `/mutation`, then `make verify`. `commands/adversary.md` owns the
trigger table; do not spawn before it is in the log. It records that decision in
`specs/<feature>/adversary-log.md` either way, so do not make it here. The order is not arbitrary: the pass
adds tests, and mutation measures whatever exists when it runs. Stop earlier only for a product decision or
unavailable input.

Once that evidence is clean, **continue on the same run**: mark the finished slice done —
{done_marker(event)} — and confirm its
`plan.md`, `research.md`, `data-model.md`, `quickstart.md` and `tasks.md` are under
`specs/<feature>/slices/<id>/` with their relative links pointing at what they cite (they have been since it
was planned; a regular file still at the feature root is moved there now, and the canonical links dropped).
Then select the next slice from the **ready** set and re-enter the ladder at whichever stage that slice's
own artifacts require, which is usually its example map or its plan rather than the top. Do not wait to be
invoked again.

{ready_set_selection(event)}

{concurrent_slices(event, layout)}

The stops are a required product decision, an input that is genuinely unavailable, a split with no ready
slice left in it, and the next slice's own demo. **A slice having finished is not one of them.**

Demo feedback re-enters the ladder at the stage that owns the change, which may sit well above the slice
loop. Re-derive the entry stage from artifacts instead of assuming the loop resumes where it paused.

{PUSH_CHECK if managed(CATALOG, target) else ""}"""


def gaps_command(event: bool) -> str:
    extra = (
        """

Compare event names, schemas, stream identity, and model links with the implementation in the same pass."""
        if event
        else ""
    )
    artifact = "a slice's `examples.md`" if event else "the slice's acceptance criteria in `spec.md`"
    return f"""---
description: Find consequential gaps in an artifact before planning, or in what was built afterwards
argument-hint: [artifact-or-feature-or-diff]
---

# Gaps

Two passes, selected by what is named. Neither invents a requirement, and a clean result is a valid outcome
when it says what was checked.

## Before planning — tighten the artifact

Named an artifact that is not built yet — {artifact}, a specification, mockups — read
`skills/find-gaps/SKILL.md` and run the conversational loop it describes: survey, ask one question at a
time, write the answer back as a new criterion or a recorded state, confirm. Missing states, unhandled
edges, unverifiable wording, and a slice still hiding an "and" are what this pass is for, and this is the
last point at which each of them is a paper edit. A gap needing a product decision is a question for the
user, never a criterion written from context.

## After implementing — trace the promise

Named a feature or diff, or nothing at all — the committed diff — read `skills/acceptance-review/SKILL.md`
and trace each acceptance promise to an observable test and a reachable production path. Report only
missing, contradictory, or unreachable behaviour, and separate a confirmed defect from a product question.
Read-only: no edits.{extra}

Run this pass **after** the installed Spec Kit converge command reports converged, never before it.
Converge appends tasks for work the artifacts require and the code lacks; ahead of it, this pass reports
unbuilt tasks as gaps and buries the findings that actually need judgement.
"""


def constitution_coverage_command(event: bool) -> str:
    scope = (
        """minimum CD, the practices this repository's skills teach, and — because `project.json` claims
the event capabilities — the Event Modeling and event-sourcing obligations."""
        if event
        else """minimum CD and the practices this repository's skills teach. The event-sourcing obligations
are not asked of this profile, and `make check-speckit` rejects a constitution that mandates them anyway."""
    )
    return f"""---
description: Check or print the principles this project's constitution must carry
argument-hint: [--requirements] [requirement-key ...]
---

# Constitution coverage

`.specify/memory/constitution.md` is what every later phase treats as the authority, so a principle
dropped from it is a gate that silently stopped existing. `scripts/check-constitution.py` states the floor:
{scope}

```sh
make check-constitution                                # what is missing, if anything
python3 scripts/check-constitution.py --requirements   # the normative text for every requirement
python3 scripts/check-constitution.py --requirements trunk-based-integration governance
```

Run the check with no arguments. With `--requirements`, print the normative text instead — that is the
drafting path, and passing requirement keys narrows it to the ones a finding named.

Amend the constitution rather than the gate, and rephrase freely: the check reads for the terms an
obligation cannot be written without, not for one wording. Where a finding needs a decision nobody has
made — the domain invariant, a retention period, a compliance scope, an unfilled `[PLACEHOLDER]` — report
which requirement is unmet and ask. An invented obligation reads as ratified afterwards, which is worse
than an open question.
"""


# Every command a generated project carries, in the order `docs/skills-and-commands.md` lists them — the last
# three reaching back out to the keel. One list, so the documentation and the files cannot disagree.
BASE_COMMANDS = ("drive", "where-are-we", "whats-next", "gaps", "adversary", "mutation", "constitution-coverage",
                 "model-delegation-settings", "drive-settings", "benchmark", "cruise", "cruise-settings",
                 "cruise-status", "cruise-stop", "cruise-tell", "cruise-watch", "add-service", "add-frontend",
                 "catch-up")
# Copied whole from `assets/profiles/event-modelling/commands/`; listed because the documentation names them in order.
EVENT_COMMANDS = ("example-map", "validate-code-against-model")


def command_names(event: bool) -> list[str]:
    """The commands this profile ships, in the order they are documented."""
    return [*BASE_COMMANDS, *(EVENT_COMMANDS if event else ())]


def command_files(
    event: bool, apps: list[App], target: str = "none", layout: Layout = AT_ROOT, adoption: Adoption | None = None,
) -> dict[str, str]:
    """`commands/`: one file per command, adapted to this profile and the services' backends."""
    files = {
        "commands/drive.md": drive_command(event, apps, target, layout, adoption),
        "commands/cruise.md": cruise_command(event, apps, target, layout, adoption),
        "commands/cruise-settings.md": cruise_settings_command(layout),
        "commands/cruise-status.md": cruise_status_command(layout),
        "commands/cruise-stop.md": cruise_stop_command(layout),
        "commands/cruise-tell.md": cruise_tell_command(layout),
        "commands/cruise-watch.md": cruise_watch_command(layout),
        "commands/where-are-we.md": where_are_we_command(event, target),
        "commands/whats-next.md": whats_next_command(event),
        "commands/gaps.md": gaps_command(event),
        "commands/adversary.md": adversary_command(event),
        "commands/mutation.md": mutation_command(backends_of(apps)),
        "commands/constitution-coverage.md": constitution_coverage_command(event),
        "commands/model-delegation-settings.md": model_delegation_settings_command(layout),
        "commands/drive-settings.md": drive_settings_command(layout),
        "commands/benchmark.md": benchmark_command(layout),
    }
    files.update(add_command_files(apps, target))
    files.update(catch_up_files(apps, target))
    return files
