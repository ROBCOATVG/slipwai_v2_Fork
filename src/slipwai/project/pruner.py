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

from ..assets import BACKING_SERVICE_ROOT
from ..registry import PRUNE_ROWS, Registry, registry

SOURCE = BACKING_SERVICE_ROOT / "prune.py"
# The keel's own line, the one place a script's rows go. Emission replaces it; a source without exactly one is refused.
ROWS_LINE = "ROWS: dict[str, dict] = {}\n"


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


def emitted(families: Iterable[str], source: str | None = None) -> str:
    """The keel's pruning script carrying the rows of these families, and no other, as the project's copy."""
    text = SOURCE.read_text() if source is None else source
    if text.count(ROWS_LINE) != 1:
        raise RuntimeError(f"the pruning script must carry exactly one `{ROWS_LINE.strip()}` line to write rows into")
    rows = json.dumps(prune_rows(families), indent=2)
    return text.replace(ROWS_LINE, f'ROWS: dict[str, dict] = json.loads(r"""\n{rows}\n""")\n')


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
