"""What `make mutation` does per backend, and why — the prose the generated Makefile carries, and the command.

Read only by the two modules that build the Makefile and the one that writes `commands/mutation.md`. The answers
are the backends' own (`mutation_note`, `mutation_tool`), and they are per backend rather than per family where
that is load-bearing: `make mutation` is run by no gate in a generated project, and by the keel's only for Go
(docs/backend-obligations.md section 2), so a note is most of what stands between the next reader and a score
they should not trust — and the two Java backends genuinely disagree, because PIT works under Spring Boot's test
harness and times out under Quarkus's. Each language's `mutation_note` answer holds its note.
"""
from __future__ import annotations

import re

from ..backends import APP
from ..registry import MUTATION_NOTE, MUTATION_SCOPING, MUTATION_TOOL, registry
from ..services import App, backends_of, services_of

# A file a note names, spelled with `APP` where the service's path goes — PIT's scope is in the pom, Gremlins'
# threshold is in its yaml — which a project with two services of one backend has two of.
NAMED_FILE = re.compile(rf"`{re.escape(APP)}/([^`]+)`")


def mutation_notes(apps: list[App]) -> str:
    """Each present backend's note once, naming that backend's own services where a note names a file. Looked up
    with a default: most backends have nothing to say about `make mutation`, and absence is that answer."""
    notes = []
    for backend in backends_of(apps):
        paths = [s.path for s in services_of(apps) if s.backend == backend]
        notes.append(named(registry().answer_or(backend, MUTATION_NOTE, ""), paths))
    return "".join(dict.fromkeys(notes))


def named(note: str, paths: list[str]) -> str:
    """Every file the note names under `APP`, as that file in each of these services, joined by "and"."""
    return NAMED_FILE.sub(lambda match: " and ".join(f"`{path}/{match[1]}`" for path in paths), note)


def mutation_command(backends: list[str]) -> str:
    answer = registry().answer
    # Each backend's `mutation_scoping` paragraph once, where it has one: how its own target narrows a run to a
    # change. Absent, nothing — most backends reach for their own tool's way of doing it.
    scoping = "".join(dict.fromkeys(registry().answer_or(b, MUTATION_SCOPING, "") for b in backends))
    return f"""---
description: Evaluate test effectiveness with mutation testing
argument-hint: [changed-production-paths]
---

# Mutation

Read `skills/mutation-testing/SKILL.md`. Target changed production code and use {" or ".join(dict.fromkeys(answer(b, MUTATION_TOOL) for b in backends)) or "the ecosystem's mutation tool"} when the
project has configured it. Mutation tooling is intentionally not part of the mandatory repository gate: if it
is absent, report the exact setup decision needed instead of pretending mutations ran. Classify survivors,
add tests only for meaningful behavioural gaps, then finish with `make verify`.
{scoping}"""
