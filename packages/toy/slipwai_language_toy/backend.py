"""The `toy` backend: one service directory of placeholder files, and an answer to every backend-level member.

Each answer has the shape the backend protocol fixes (slipwai's `registry` module, and its backend-protocol contract)
and none of the substance: the commands say what a real language would run and exit 0, the event stores are
placeholder files (the in-memory one the axis always ships, and Postgres), and nothing is deployed (`targets:
["none"]` in `language.json`). Replace them one at a time, with the conformance suite running, until the package is
your language.

The files the answers write are under `assets/` beside this package: `languages/toy/…` for the service skeleton, its
flag reader and its example snippets, `backing-services/toy/…` for what each persistence answer adds.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from slipwai import registry as protocol
from slipwai.assets import asset_tree
from slipwai.backends import APP, Tooling
from slipwai.project.backing_services import backing_service_service_files
from slipwai.project.flags import FlagReader, flag_reader
from slipwai.selection import Selection
from slipwai.services import App
from slipwai.tooling import for_app

from .family import FAMILY_ANSWERS

ASSETS = Path(__file__).resolve().parents[1] / "assets"
# The token the skeleton carries where the service's name goes, resolved by `name_service`.
SERVICE_NAME = "__SERVICE_NAME__"
# The backend's key: the family's name and its framework's, because the bare `toy` names what the family's
# backends share (`assets/languages/toy/`, `assets/backing-services/toy/`), and a framework added beside this one
# then renames nothing.
KEY = "toy-plain"


def placeholder(what: str) -> str:
    """A command that says what a real language would do here, and succeeds."""
    return f"@echo 'toy: a real language would {what} in {APP}'"


def service_files(event: bool, selection: Selection, target: str = "none") -> dict[str, str]:
    """What this backend puts in a service's directory, keyed relative to it.

    `event` says only that the project is on the modelled profile, and is deprecated: it was all a backend
    had to go on when Event Modeling and event sourcing were one answer. The rung is per service and is
    `selection.option("write-model")` — which `backing_service_service_files` reads below, so a backend
    whose two rungs differ only in which files they are given never asks the question itself.
    """
    files = asset_tree(ASSETS / "languages/toy/app")
    # What each answered axis adds, read from `write_side_files` and `read_side_files` by core.
    files.update(backing_service_service_files(selection, KEY))
    # The flag reader, which core writes only where there is somewhere to deploy; `none` gets nothing.
    files.update(flag_reader(target, KEY))
    return files


def name_service(project_name: str, service: App, files: dict[str, str]) -> dict[str, str]:
    """One service's files under this project's own names: here, the token in the skeleton."""
    for path in list(files):
        if path.startswith(f"{service.path}/"):
            files[path] = files[path].replace(SERVICE_NAME, f"{project_name}-{service.name}")
    return files


def repository_files(project_name: str, files: dict[str, str], services: list[App], verify: str) -> dict[str, str]:
    """What the family writes once above its services: here only the verify script, which a real language's gate is."""
    apps = " ".join(service.path for service in services)
    files[verify] = (
        f"#!/bin/sh\nset -eu\nfor app in {apps}; do\n  echo \"toy: a real language verifies $app here\"\ndone\n"
    )
    return files


def native_commands(path: str, verify: str) -> dict[str, str]:
    """One service's eight Makefile targets (`native_commands.TARGETS`), spelled for its own directory."""
    targets = ("install", "typecheck", "lint", "test", "integration", "adversarial", "audit", "mutation")
    return {target: for_app(placeholder(f"run {target}"), path, verify) for target in targets}


def dev_command(qualifier: str, path: str, verify: str) -> str:
    """How one service starts in the foreground."""
    return f"echo 'toy: a real language starts {path} here'"


def persistence_directory(path: str) -> str:
    """Where one service's driven adapters live, for prose that points at them.

    One answer for both rungs: the event store's adapters and the repository's land in the same directory
    here, as they do in most layouts, and the prose that reads this says which of the two it is talking
    about. The member was called `event_store_directory` until the rung became a question.
    """
    return f"{path}/adapters/"


TOOLING: Tooling = {
    "install": placeholder("install dependencies"),
    "migrate": placeholder("apply migrations"),
    "integration": placeholder("run the integration suite"),
    "ci_image": "debian:bookworm-slim",
    "ci_install": placeholder("install dependencies"),
    "container_setup": "",
    "container_environment": {},
}

# Feature → where it lands in the service → the asset, relative to `assets/backing-services/toy-plain/`, so `../toy/`
# is the family's copy, which a framework beside this one reads too. The persistence axis always ships `memory` beside
# whichever store is chosen, so both sides answer it and every store offered; a real language adds a row per store,
# transport and provider it offers. `postgres` is offered because an axis whose only answer is `memory` is never asked,
# so a project would get no store files, and because core's persistence default is `postgres`, which every backend
# offering a second store must offer.
# `state` is not a feature: it is the other rung, and the rows under it are what a service answered
# `write-model: state` is given instead of the ones above — the repository port and its adapters where the
# event-sourced service gets the log, and the migration for a versioned state table. Keyed by feature inside
# the block the same way, because the rung does not settle which store was chosen.
WRITE_SIDE = {
    "memory": {"adapters/event_store_memory.txt": "../toy/event_store_memory.txt"},
    "postgres": {"adapters/event_store_postgres.txt": "../toy/event_store_postgres.txt"},
    "state": {
        "memory": {"adapters/repository_memory.txt": "../toy/repository_memory.txt"},
        "postgres": {"adapters/repository_postgres.txt": "../toy/repository_postgres.txt",
                     "migrations/0001_state_table.txt": "../toy/state_table_migration.txt"},
    },
}
# No checkpoint on the state-stored rung: there is no projection to be behind, so a read model is a query
# over the write tables and the only row is the store that holds them.
READ_SIDE = {
    "memory": {"adapters/checkpoint_store_memory.txt": "../toy/checkpoint_store_memory.txt"},
    "postgres": {"adapters/checkpoint_store_postgres.txt": "../toy/checkpoint_store_postgres.txt"},
    "state": {"postgres": {"adapters/read_tables_postgres.txt": "../toy/read_tables_postgres.txt"}},
}

# Where the flag reader is committed (`assets/languages/toy/flags`), where it lands, and how a slice asks it.
READER = FlagReader(
    tree="toy/flags", source="flags/flags.txt", tests="flags/flags_test.txt", call='flag("checkout-v2")'
)

ANSWERS: dict[protocol.Member[Any], object] = {
    protocol.SERVICE_FILES: service_files,
    protocol.NAME_SERVICE: name_service,
    protocol.REPOSITORY_FILES: repository_files,
    protocol.READY_PATH: "/ready",
    protocol.HEALTH_BODY: '{"status":"ok"}',
    protocol.TOOLING: TOOLING,
    protocol.FEATURE_TOOLING: {},
    protocol.EXECUTABLES: frozenset(),
    protocol.DEV_COMMAND: dev_command,
    protocol.COMPOSE_CACHES: (),
    protocol.PERSISTENCE_DIRECTORY: persistence_directory,
    protocol.NATIVE_COMMANDS: native_commands,
    protocol.IMAGE_BUILDER: {"tool": "toy", "build": placeholder("build an image")},
    protocol.MIGRATIONS_IN_PRODUCTION: {"command": ["echo", "toy: a real language migrates here"]},
    # Every managed-database kind core declares, answered; None is an answer.
    protocol.POSTGRES_SSLMODE: {"rds": None, "flexible-server": None},
    protocol.SERVICE_DESCRIPTORS: {},
    protocol.WRITE_SIDE_FILES: WRITE_SIDE,
    protocol.READ_SIDE_FILES: READ_SIDE,
    protocol.FLAG_READER: READER,
    protocol.ENTRY_WIRING: {},
    protocol.FLAG_RESOURCE: {},
    # None: no composition root for core to write the store's opening into.
    protocol.ENTRY_STORE: None,
    protocol.GITIGNORE: "",
    protocol.AGENT_PERMISSIONS: [],
    protocol.GATE_DESCRIPTION: "placeholders that echo what a real language's gate would run",
    # `repository` is read only by a service on the state-stored rung: the port it loads and saves current
    # state through, where an event-sourced service has the event-store port. Every language answers it,
    # whichever rung its projects are generated on, because the rung is the project maker's answer and not
    # the language's.
    protocol.EVENT_MODEL_PATHS: lambda project_name, service: {
        "events": f"{service}/domain/<context>/events.txt",
        "domain": f"{service}/domain/<context>/decider.txt",
        "usecase": f"{service}/application/<context>/usecase.txt",
        "test": f"{service}/domain/<context>/<slice>_test.txt",
        "repository": f"{service}/application/<context>/repository.txt",
    },
    protocol.MUTATION_TOOL: "none (the toy language has no mutation tool)",
    protocol.PROCFILE: None,
    protocol.OPT_IN_FLAG_TRANSPORTS: frozenset(),
}

LANGUAGE = protocol.Language(
    (protocol.Family("toy", FAMILY_ANSWERS),),
    (protocol.Backend(KEY, "toy", ANSWERS),),
)
