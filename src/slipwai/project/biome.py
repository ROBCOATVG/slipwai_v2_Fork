"""`biome.jsonc` and the domain-purity plugin beside it: the npm workspace's lint and format gate.

One configuration at the repository root rather than one per package, because a formatter with two
opinions is a diff that moves back and forth depending on which directory it was run from. Every npm
package in the project — each Node service, each browser app, anything shared under `packages/` — spells
`lint` as `biome check`, which finds this file by walking up from wherever npm started it. The `.jsonc`
extension and not `.json`: the configuration is worth a paragraph of reasons, and Biome reads comments
only in the one it can parse as JSONC.

It is written whenever the project has an npm workspace at all, which is the condition that decides
whether there is a root `package.json` (`shared_packages.node_workspace`): a Python or Go service beside a
React browser app still has TypeScript to lint, and that browser app had no linter before this.

The pinned Biome is read back out of the service manifest rather than written down a second time here —
the version in the `$schema` URL and the version npm installs have to be the same one, and the manifest is
the one npm locks.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..assets import FRONTEND_ROOT
from ..npm_workspace import NpmWorkspace, browser_language, workspace
from ..services import App
from .shared_packages import node_workspace

VERSION = "__BIOME_VERSION__"
# Where the plugin lands, and what `biome.json` names it as. Root-relative rather than `./`-prefixed so
# that `Layout.repoint` moves the pointer with the directory when the delivery material lives elsewhere.
PLUGIN = "scripts/domain-purity.grit"


def pinned_in(answer: NpmWorkspace | None = None) -> tuple[Path, ...]:
    """Where the pin lives: the manifests that declare the dependency, the workspace language's and the browser
    app's. They must agree, because npm hoists one copy to the workspace root and a project with two would lint
    itself with whichever won."""
    answer = workspace(browser_language()) if answer is None else answer
    return (*answer.biome_pins, FRONTEND_ROOT / "react-vite/app/package.json")


def biome_version(answer: NpmWorkspace | None = None) -> str:
    """The exact `@biomejs/biome` the manifests pin."""
    pins = {
        json.loads(path.read_text())["devDependencies"]["@biomejs/biome"] for path in pinned_in(answer)
    }
    if len(pins) != 1:
        raise AssertionError(f"the manifests pin more than one Biome: {sorted(pins)}")
    return pins.pop()


def biome_files(apps: list[App]) -> dict[str, str]:
    """The configuration and its plugin, or nothing at all in a project with no npm workspace."""
    if not node_workspace(apps):
        return {}
    # The workspace runs one Biome, the first workspace language's: the one a browser app is written in.
    answer = workspace(browser_language())
    return {
        "biome.jsonc": (answer.biome / "biome.jsonc").read_text().replace(VERSION, biome_version(answer)),
        PLUGIN: (answer.biome / "domain-purity.grit").read_text(),
    }
