"""One module per backend language: the walking skeleton, its manifests, and its own naming.

Each language owns the whole of its own contribution — what lands in a service's directory, and how the
template names become this project's. No shared rename step: a backend brings its own `name_service`. These are
the languages built into the keel; a language may also be a package in the package directory, which the keel loads
by name and this module never lists."""
from __future__ import annotations

from ...registry import NAME_SERVICE, REPOSITORY_FILES, SERVICE_FILES, Language, registry
from ...services import App, families_of, services_of
from ...tooling import verify_dispatcher, verify_path

# What the keel discovers of the languages built into it: each module's `LANGUAGE`, imported statically here so the
# frozen executable's analysis follows it. The keel is built with none today — every language is a package, loaded
# from the package directory by `slipwai.loaded` and listed nowhere here — and the path stays for one that is.
LANGUAGES: tuple[Language, ...] = ()


def language_files(project_name: str, event: bool, apps: list[App], target: str = "none") -> dict[str, str]:
    """Everything every backend contributes, at its final paths and under its final names.

    `service_files` is keyed relative to the service — the only thing this facade knows about any backend —
    and is emitted once per service from its own selection and the target (which decides only whether the
    service gets a flag reader), then named for it. Root files come from `repository_files`, once per
    language family; with several families, `scripts/verify` dispatches to each."""
    services = services_of(apps)
    files: dict[str, str] = {}
    answer = registry().answer
    for service in services:
        built = answer(service.backend, SERVICE_FILES)(event, service.selection, target)
        tree = {f"{service.path}/{p}": t for p, t in built.items()}
        files.update(answer(service.backend, NAME_SERVICE)(project_name, service, tree))
    for family in families_of(apps):
        own = [service for service in services if service.language == family]
        repository_files = answer(own[0].backend, REPOSITORY_FILES)
        files = repository_files(project_name, files, own, verify_path(family, apps))
    if len(families_of(apps)) > 1:
        files["scripts/verify"] = verify_dispatcher(apps)
    return files
