"""The project's one npm workspace, as the keel asks about it: which languages are in it, and what a browser app is.

A browser app is an npm package, and so is every service of a language whose code npm installs. The keel's `react-vite`
frontend owns the browser app and the workspace's root; a language joins the workspace by answering
`npm_workspace` on its family, with what only it knows: its services' committed locks, the lock of a workspace
that holds one of them beside a browser app, the image a browser app's dev server runs in, and the lint and format
configuration every package in the workspace shares. The keel never names the language: it asks the registry
(`contracts/npm-workspace.md`, FR-034, D50).

A browser app is written in the first family, in registry order, that answers the member. With none loaded there
is no language to write one in, and asking for one is refused in a line (S09's Q1).
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple, cast

from .errors import GenerationError
from .registry import NPM_WORKSPACE, Registry, registry

# What a refusal for a browser app with no language to write it in says first. Each verb says what it was asked, and
# `browser_app` how it ends: the language the index says answers, and its install line (D122, over D63).
BROWSER = "needs a language that answers the npm workspace, and none is loaded"


class NoBrowserLanguage(GenerationError):
    """No loaded family answers `npm_workspace`: the verb that meets it says which language would (`browser_app`)."""


class NpmWorkspace(NamedTuple):
    """What a language tells the keel about its part of the npm workspace (`contracts/npm-workspace.md`)."""

    member_lock: Callable[[Any], Path]
    """One of its services' committed `package-lock.json`, for that service's selection."""
    workspace_lock: Callable[[Any, str], Path]
    """The workspace lock for a first member service of this selection beside browser apps whose lock suffix is the
    `str` (`''` or `-users-keycloak`)."""
    image: str
    """The image a browser app's dev server runs in, under Compose."""
    biome: Path
    """The directory holding `biome.jsonc` and `domain-purity.grit`, the workspace's one lint and format gate."""
    biome_pins: tuple[Path, ...]
    """Its manifests that pin `@biomejs/biome`, which must agree with the browser app's."""


def workspaces(held: Registry | None = None) -> dict[str, NpmWorkspace]:
    """Each family of `held` (the process's registry by default) that answers `npm_workspace`, in registry order."""
    families = (registry() if held is None else held).families
    return {
        name: cast(NpmWorkspace, family.answers[NPM_WORKSPACE])
        for name, family in families.items()
        if NPM_WORKSPACE in family.answers
    }


def npm(language: str) -> bool:
    """Whether a family's code is an npm package in the project's workspace."""
    return language in workspaces()


def browser_language() -> str:
    """The family a browser app is written in: the first that answers `npm_workspace`."""
    found = next(iter(workspaces()), None)
    if found is None:
        raise NoBrowserLanguage(f"a browser app {BROWSER}")
    return found


def workspace(language: str) -> NpmWorkspace:
    """A family's answer to `npm_workspace`."""
    return workspaces()[language]


def held_lock(language: str, field: str, path: object, root: Path | None = None) -> Path:
    """The lock a family answered `field` with, refused in one line where it is not a file inside the family's
    package (`root`, the registry's by default) — at generation, since a lock is answered for a selection."""
    home = (registry().root(language) if root is None else root).resolve()
    if not isinstance(path, Path):
        raise GenerationError(f"family {language} answers {field} with {type(path).__name__}, where a Path is wanted")
    if not path.resolve().is_relative_to(home):
        raise GenerationError(f"family {language} reaches outside its directory for {field}")
    if not path.is_file():
        raise GenerationError(f"family {language} reaches for {field}, which is not a file in its directory")
    return path
