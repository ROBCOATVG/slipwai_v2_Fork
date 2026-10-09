"""Fake languages for the registry's tests: objects written here, against the real protocol.

Not a test module. Every fake answers through the same `Member` constants a real language does, so a fake
that goes wrong does so in exactly the one way its test names.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from slipwai.registry import (
    AGENT_PERMISSIONS,
    CI_TOOLCHAIN_SETUP,
    COMPOSE_CACHES,
    DEV_COMMAND,
    ENTRY_STORE,
    ENTRY_WIRING,
    EVENT_MODEL_PATHS,
    EXECUTABLES,
    FEATURE_TOOLING,
    FLAG_READER,
    FLAG_RESOURCE,
    FORMATTER,
    GATE_DESCRIPTION,
    GITIGNORE,
    HEALTH_BODY,
    IMAGE_BUILDER,
    MAKEFILE_VARIABLES,
    MIGRATIONS_IN_PRODUCTION,
    MUTATION_TOOL,
    NAME_SERVICE,
    NATIVE_COMMANDS,
    OPT_IN_FLAG_TRANSPORTS,
    PERSISTENCE_DIRECTORY,
    PIN_FILES,
    POSTGRES_SSLMODE,
    PROCFILE,
    PRUNE_ROWS,
    READ_PER_FAMILY,
    READ_SIDE_FILES,
    READY_PATH,
    RENOVATE_RULES,
    REPOSITORY_FILES,
    SERVICE_DESCRIPTORS,
    SERVICE_FILES,
    SHARED_CODE,
    TOOLING,
    WRITE_SIDE_FILES,
    Backend,
    Family,
    Language,
    Member,
    Registry,
    load,
)

# Which fault `LANGUAGES` injects into `FAULTY`: "missing" takes its `ready_path`, "string-key" adds an answer keyed by
# a plain string, "bad-rows" answers `prune_rows` with a manifest no uninstaller handles, "none" injects nothing (a
# sound built-in, for what core says of a language built into it: D52).
# A subprocess sets it before the command line starts.

class FlagReader:
    """Stands in for `project.flags.FlagReader`, which arrives in phase 3. The protocol asks for an object."""

    def __init__(self, tree: str, source: str, tests: str, call: str) -> None:
        self.tree, self.source, self.tests, self.call = tree, source, tests, call


class RenovateRules(tuple):
    """Stands in for `project.renovate.RenovateRules`, which arrives in phase 3. The protocol asks for a tuple."""


def no_files(*_arguments: object) -> dict[str, str]:
    """Stands in for every callable member: a language that generates nothing."""
    return {}


def no_setup(*_arguments: object) -> str:
    """Stands in for a family's CI toolchain step: a language whose CI installs nothing."""
    return ""


def event_model_paths(project_name: str, service: str) -> dict[str, str]:
    """Stands in for `event_model_paths`: the five keys the documents read, under the service."""
    return {key: f"{service}/{key}" for key in ("events", "domain", "usecase", "test", "repository")}


def rows(**overrides: object) -> dict[str, object]:
    """A family's `prune_rows` the pruner can read, owning nothing, with any key a test overrides."""
    return {"marked_files": (), "owned_files": {}, "package_edits": {}, "manifest": None, **overrides}


def required_answers(
    without: tuple[Member[Any], ...] = (), extra: Mapping[Member[Any], object] | None = None
) -> dict[Member[Any], object]:
    """An answer to each required member, minus those named, plus whatever a test adds or overrides."""
    answers: dict[Member[Any], object] = {
        SERVICE_FILES: no_files,
        NAME_SERVICE: no_files,
        REPOSITORY_FILES: no_files,
        READY_PATH: "/ready",
        HEALTH_BODY: '{"status":"ok"}',
        TOOLING: dict.fromkeys(("install", "migrate", "integration", "ci_image", "ci_install", "container_setup"), "")
        | {"container_environment": {}},
        FEATURE_TOOLING: {},
        COMPOSE_CACHES: (),
        EXECUTABLES: frozenset(),
        DEV_COMMAND: no_files,
        PERSISTENCE_DIRECTORY: no_files,
        NATIVE_COMMANDS: no_files,
        FORMATTER: None,
        # S03's members: a backend that builds no image, migrates nothing and sets no toolchain up.
        IMAGE_BUILDER: {"tool": "", "build": ""},
        MIGRATIONS_IN_PRODUCTION: {},
        POSTGRES_SSLMODE: {"rds": None, "flexible-server": None},
        SERVICE_DESCRIPTORS: {},
        CI_TOOLCHAIN_SETUP: no_setup,
        WRITE_SIDE_FILES: {},
        READ_SIDE_FILES: {},
        FLAG_READER: FlagReader(tree="fake/flags", source="flags.x", tests="flags_test.x", call="enabled()"),
        ENTRY_WIRING: {},
        FLAG_RESOURCE: {},
        ENTRY_STORE: None,
        SHARED_CODE: "a package under `packages/<name>`",
        PRUNE_ROWS: rows(),
        # S05's: a backend whose toolchain writes nothing to ignore and needs no permission of its own.
        GITIGNORE: "",
        AGENT_PERMISSIONS: [],
        GATE_DESCRIPTION: "the fake gate",
        EVENT_MODEL_PATHS: event_model_paths,
        MUTATION_TOOL: "the fake mutator",
        PROCFILE: None,
        PIN_FILES: {},
        MAKEFILE_VARIABLES: None,
        RENOVATE_RULES: RenovateRules(),
        OPT_IN_FLAG_TRANSPORTS: frozenset(),
    }
    for member in without:
        del answers[member]
    answers.update(extra or {})
    return answers


class UnreadableAnswers(Mapping[Any, object]):
    """A mapping that is one by type and breaks when asked whether it holds a member."""

    def __getitem__(self, key: Any) -> object:
        raise KeyError(key)

    def __iter__(self) -> Iterator[Any]:
        return iter(())

    def __len__(self) -> int:
        return 0

    def __contains__(self, key: object) -> bool:
        raise TypeError("cannot be asked")


def family_answers() -> dict[Member[Any], object]:
    """What a family answers for its backends because core reads it from the family (`READ_PER_FAMILY`, and
    `formatter` for the family a browser app is written in)."""
    return {m: answer for m, answer in required_answers().items() if m in READ_PER_FAMILY or m == FORMATTER}


def per_family(extra: Mapping[Member[Any], object] | None = None) -> dict[Member[Any], object]:
    """A family's answers to what core reads per family (`READ_PER_FAMILY`), plus whatever a test adds."""
    return {m: answer for m, answer in required_answers().items() if m in READ_PER_FAMILY} | dict(extra or {})


def per_backend(
    without: tuple[Member[Any], ...] = (), extra: Mapping[Member[Any], object] | None = None
) -> dict[Member[Any], object]:
    """`required_answers` less what core reads per family, which `per_family` puts on the family as a real one does."""
    shed = set(READ_PER_FAMILY) | set(without)
    return {m: answer for m, answer in required_answers().items() if m not in shed} | dict(extra or {})


def fake_language(key: str, family: str = "fake", answers: Mapping[Member[Any], object] | None = None) -> Language:
    """One backend and, beside it, its own family, holding what core reads per family (`READ_PER_FAMILY`) as a real
    family does; the backend answers the rest."""
    return Language(*split(key, family, required_answers() if answers is None else answers))


def split(
    key: str, family: str, answers: Mapping[Member[Any], object]
) -> tuple[tuple[Family, ...], tuple[Backend, ...]]:
    """`answers` divided between a family and its backend as `load` holds them: per-family members on the family.
    Only a plain dict is divided: anything else — a mapping that breaks when read, one that raises when asked, not a
    mapping at all — is the fault a test hands `load`, so it goes to the backend unread, for `load` to be the one
    that reads it, and not the package's import."""
    if type(answers) is not dict:
        return (Family(family),), (Backend(key, family, answers),)
    own = {member: answer for member, answer in answers.items() if member in READ_PER_FAMILY}
    rest = {member: answer for member, answer in answers.items() if member not in own}
    return (Family(family, own),), (Backend(key, family, rest),)


def fake_registry(*languages: Language, roots: Mapping[str, Path] | None = None) -> Registry:
    """A registry of fake languages whose owners' assets sit at `roots`, as a loaded package's would."""
    return replace(load(languages), roots=roots or {})
