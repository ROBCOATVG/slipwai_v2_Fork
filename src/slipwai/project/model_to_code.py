"""The document that says what each box on the model becomes in a file, per service.

Its own module because it is most of the bytes and none of the behaviour: `event_model.py` computes the
per-backend paths and this renders them, which is the same split the service layouts were on the other side
of. One page, generated per project, because the paths in it are the project's own.

A section per service rather than one table for the project, because the write model is per service and the
table is the write model written out: the same `evt` on the timeline is a record appended to a log in one
service and a file the use case raises after a row is saved in the next, and a reader told only the first
will write a fold into a service that keeps no history to fold.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceCode:
    """One service's section of the page: where it is, which rung it is on, and where its code lands.

    The rung arrives as the answer `metadata.sourced` already gave rather than as the axis's word, so this
    module has no second opinion about what `events` means and never has to be kept in step with one.

    `paths` is the backend's `event_model_paths` with `repository` always in it (`event_model.code_paths`),
    which only the state-stored section reads: on the other rung the store a write is appended to is the
    event-store port, and that is named in the write-model table rather than here.
    """

    path: str
    sourced: bool
    paths: dict[str, str]


def heading(service: ServiceCode) -> str:
    """The section heading, which says the rung in the words the rung is about rather than by its key.

    `write-model: events` is what `project.json` says and what a flag answers; *the log is the truth* is
    what a person has to hold in their head while reading the table under it.
    """
    claim = "the log is the truth" if service.sourced else "current state is the truth"
    return f"## `{service.path}` — {claim}"


def event_sourced_section(service: ServiceCode) -> str:
    """The table and the rules for a service whose state is a fold of its own events."""
    paths = service.paths
    return f"""{heading(service)}

This service answers `write-model: events`: current state is a fold of what happened, and a write is an
append made at an expected version of a stream.

| Model element | Code responsibility | Initial location |
|---|---|---|
| `ui` | actor-facing surface plus driving adapter | application-specific surface under `{service.path}` |
| `cmd` | typed intent and application use case | `{paths['usecase']}` |
| `evt` | immutable, versioned fact, appended to its stream | `{paths['events']}` |
| the decision | a Decider: `evolve` folds the stream into state, `decide` returns new events or an explicit rejection | `{paths['domain']}` |
| `rmo` | pure fold, plus the store its slice's `materialisation` names | application module, plus a driven adapter for anything but `live` |
| `pcr` | processor that reads, decides, and issues a command | `{paths['usecase']}` |
| `stream` | aggregate identity and optimistic-concurrency boundary | domain identity plus the event-store port |
| `guard` | the other boundary: a tag query and the position it was read at, which `appendIf` is refused by | the project's tagging function, plus the conditional append at the use case |
| `evt`'s `attributes` | the payload's fields; the ones marked `identifies:` become the event's tags | the event, plus the tagging function the store is built with |

Keep decision logic pure: rehydrate state by folding events, decide from state plus a command, and return
new events or an explicit rejection. The application layer loads history, invokes the decision, and appends
with an expected version. Infrastructure implements ports; it does not enter domain code.

A read model is a pure fold in all three cases, and `materialisation` on the slice says what maintains it:
`live` folds it per query and stores nothing, `inline` writes it in the append's own transaction, `async`
maintains it from a catch-up subscription whose checkpoint advances in the same transaction as the view.
`make check-model` requires the field from `planned` for the same reason it requires a guard — the event
store ships with `read`, `append` and a replay from position zero and nothing else, so a per-query fold is
the only read path that is already there, and a slice never asked ships with every query paying for the
whole log. A `live` view names `liveBudget` too: the ceiling one query may fold, and why that ceiling holds
in terms of the stream's own lifetime.
"""


def state_stored_section(service: ServiceCode) -> str:
    """The table and the rules for a service that keeps current state and raises its events afterwards.

    Two rows say *refused* rather than being left out. A field missing from a table reads as a field nobody
    thought about, and `guard` and `folds` are on the timeline of every slice this project's modelling skill
    teaches — so the table has to say they are refused here and why, or the first slice written against this
    service names one and finds out at the gate.
    """
    paths = service.paths
    return f"""{heading(service)}

This service answers `write-model: state`: it keeps the current state of what it owns, and the events the
model names are contracts raised once a write has committed and never replayed.

| Model element | Code responsibility | Initial location |
|---|---|---|
| `ui` | actor-facing surface plus driving adapter | application-specific surface under `{service.path}` |
| `cmd` | typed intent and application use case | `{paths['usecase']}` |
| `evt` | immutable, versioned fact, raised by the use case once the write has committed | `{paths['events']}` |
| the decision | a load through the repository port, a pure decide over current state, and a save at the version that was read | `{paths['domain']}`, loading and saving through `{paths['repository']}` |
| `rmo` | pure fold, plus the store its slice's `materialisation` names | application module, plus a driven adapter for anything but `live` |
| `pcr` | processor that reads, decides, and issues a command | `{paths['usecase']}` |
| `stream` | the row or aggregate one transaction locks, and the version it is saved at | domain identity plus `{paths['repository']}` |
| `guard` | refused on this rung by name: a tag query reads a log, and this service keeps none | — |
| `folds` | refused for the same reason — there is no history here to fold | — |
| `evt`'s `attributes` | the payload's fields; the ones marked `identifies:` name what the fact is about | the event the use case raises |

Keep decision logic pure: load current state through the repository port, decide from that state plus a
command, and return the new state together with the events the slice says the write raises. The application
layer saves at the version it read — a save at a version somebody else has already moved past is the
rejection, and it is the whole of the concurrency control here — and raises the events after the save
commits. Infrastructure implements ports; it does not enter domain code.

Nothing in this service is rebuilt from its past, and that is the trade this rung makes: a write is one row
and one version, and how that row came to hold what it holds is not recorded. So an event raised here is
true from the moment it is raised and claims nothing about what came before it — never write one that
asserts a fact the service did not observe at the time.

A read model is a pure fold in all three cases, and `materialisation` on the slice says what maintains it:
`live` is a query over the write tables themselves, `inline` is written in the write's own transaction, and
`async` is maintained from the outbox the raised events are published through. `make check-model` requires
the field from `planned`, and asks no `liveBudget` on this rung — a `live` view reads current state rather
than folding a log, so there is no ceiling of events for it to name.
"""


def model_to_code(services: list[ServiceCode]) -> str:
    """`docs/event-modeling-to-code.md`, with one section per service and the project's own paths in it."""
    placing = (
        """A slice names the service it belongs to in `model.yaml`'s `service` field, decided against what each
service says it owns — the `purpose` on its `project.json` entry, listed under *Bounded contexts* in
`docs/architecture.md`. With one service the field is optional; with two or more, `make check-model`
requires it, because a slice that names no owner lands in the first service by gravity, not by decision."""
        if len(services) == 1
        else """A slice names the service it belongs to in `model.yaml`'s `service` field, decided against what each
service says it owns — the `purpose` on its `project.json` entry, listed under *Bounded contexts* in
`docs/architecture.md`. `make check-model` requires it here, because a slice that names no owner lands in
the first service by gravity, not by decision — and because with more than one write model in the project,
naming the service is what settles which table below the slice is read against."""
    )
    sections = "\n".join(
        event_sourced_section(service) if service.sourced else state_stored_section(service)
        for service in services
    )
    # Named per service only where there is more than one, so the single-service page keeps the sentence it
    # has always had rather than growing a prefix that answers a question nobody has.
    examples = "\n".join(
        f"- Express agreed examples as observable tests using `{service.paths['test']}`."
        if len(services) == 1
        else f"- In `{service.path}`, express agreed examples as observable tests using "
             f"`{service.paths['test']}`."
        for service in services
    )
    return f"""# From event model to code

The model describes behavior; the services under `apps/` make it executable.
{placing}
`<context>` in the paths below is the slice's `context` where the service holds several bounded contexts
(its `contexts` in `project.json`; the gate requires the field then too), and the service's one context
otherwise. Names are illustrative—domain names come from modelling.

{sections}
## Testing by responsibility

{examples}
- Test pure decision tables directly only for meaningful combinatorial rules.
- Run every port contract against both its fake and real adapter.
- Test driven integrations against realistic stubs for parsing, timeout, retry, and error translation.
- Test delivery adapters for parsing and outcome mapping; do not duplicate domain rules there.
- Keep Python tests on pytest, Go tests on `testing`, and TypeScript tests on Vitest—the repository gate
  already invokes the canonical stack.

Event names, payloads, the identity each write is made against, `reads`, tests, and code paths change as one
contract. Use `/validate-code-against-model` to report drift rather than silently changing either side.
"""
