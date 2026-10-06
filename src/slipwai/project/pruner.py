"""The pruning script a project carries, and the keel's own copy of it: the keel's one implementation, with rows.

`assets/backing-services/prune.py` names no language. What it needs to know about one (which files in a service
carry marker regions, which a feature owns, what a feature added to the manifest and how that is removed) is
each family's `prune_rows`, answered in its language module. This part reads those answers from the registry
and gives them to the script two ways:

- `emitted` is what a generated project carries as `scripts/backing-services.py`: the keel's source with its one
  empty `ROWS` line replaced by the rows of the project's families, as JSON the script reads.
- `pruner` is what the keel itself prunes with at generation, `add-service` and `replay`: the same file,
  loaded, with every loaded family's rows. `assets.PRUNER` is the keel's copy with none, which is what the catalog
  checks read for the facts that are not rows. It cannot read the registry itself, because `assets` is the
  foundation tier and the registry is not (`scripts/check-structure.py`).

The format is fixed in `specs/001-slipwai-2-language-addons/contracts/backend-protocol.md`, `prune_rows`.
"""
from __future__ import annotations

import functools
import importlib.util
import json
from collections.abc import Iterable
from types import ModuleType
from typing import Any

from ..assets import BACKING_SERVICE_ROOT, ROOT
from ..catalog import CATALOG
from ..registry import PRUNE_ROWS, Registry, registry

SOURCE = BACKING_SERVICE_ROOT / "prune.py"
# The keel's own line, the one place a script's rows go. Emission replaces it; a source without exactly one is refused.
ROWS_LINE = "ROWS: dict[str, dict] = {}\n"
OPTIONS_LINE = "AXIS_OPTIONS: dict[str, dict] = {}\n"


def family_rows(loaded: Registry, family: str) -> dict | None:
    """One family's rows, read through its first backend, so a family answer and a backend's are read alike.

    A family with no loaded backend (its frameworks absent or refused) has nothing to prune and answers None.
    """
    backend = next((key for key, candidate in loaded.backends.items() if candidate.family == family), None)
    return None if backend is None else dict(loaded.answer(backend, PRUNE_ROWS))


def prune_rows(families: Iterable[str]) -> dict[str, dict]:
    """The rows of these families, keyed by family, in the order given; a family with no backend has none."""
    loaded = registry()
    rows = {family: family_rows(loaded, family) for family in families}
    return {family: answer for family, answer in rows.items() if answer is not None}


def axis_options(catalog: dict[str, Any] | None = None) -> dict[str, dict]:
    """Every axis option a package brought, keyed by axis, in the shape the pruner's own table takes.

    The keel's copy of the pruner carries the infrastructure answers and no framework: an option named
    after a library — `fastapi`, `spring-web` — belongs to the package that implements it. They are
    written into a generated project's copy from the merged catalogue, the way each family's rows are,
    so a project prunes by the options it was actually offered.
    """
    merged = CATALOG if catalog is None else catalog
    keel = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))["axes"]
    brought: dict[str, dict] = {}
    for axis, spec in merged["axes"].items():
        own = set(keel.get(axis, {}).get("options", {}))
        for name, option in spec["options"].items():
            if name in own:
                continue
            brought.setdefault(axis, {})[name] = {
                "capabilities": list(option.get("capabilities", ())),
                "features": list(option.get("features", ())),
                "targets": list(option.get("targets", ())),
                "label": option.get("label", ""),
                "note": option.get("note", ""),
                "app-in-compose": bool(option.get("app-in-compose")),
                "repository-owned": list(option.get("repository-owned", ())),
                "web-app-owned": list(option.get("web-app-owned", ())),
            }
    return brought


def emitted(families: Iterable[str], source: str | None = None) -> str:
    """The keel's pruning script carrying the rows of these families and the options their packages
    brought, and nothing of any other, as the project's copy."""
    text = SOURCE.read_text(encoding="utf-8") if source is None else source
    for line in (ROWS_LINE, OPTIONS_LINE):
        if text.count(line) != 1:
            raise RuntimeError(f"the pruning script must carry exactly one `{line.strip()}` line to write into")
    rows = json.dumps(prune_rows(families), indent=2)
    options = json.dumps(axis_options(), indent=2)
    text = text.replace(ROWS_LINE, f'ROWS: dict[str, dict] = json.loads(r"""\n{rows}\n""")\n')
    return text.replace(OPTIONS_LINE, f'AXIS_OPTIONS: dict[str, dict] = json.loads(r"""\n{options}\n""")\n')


@functools.cache
def pruner() -> ModuleType:
    """The keel's pruner: the keel's script, loaded, with every loaded family's rows in the shape a project reads."""
    spec = importlib.util.spec_from_file_location("slipwai_factory_pruner", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load the backing-service pruner from {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    vars(module)["ROWS"] = json.loads(json.dumps(prune_rows(registry().families)))
    return module
