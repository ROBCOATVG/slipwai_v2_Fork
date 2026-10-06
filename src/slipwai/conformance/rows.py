"""The `prune rows` check: `./init` prunes what a family's rows name, so what the rows miss a prune leaves behind.

The loader already refuses rows the pruning script cannot read (`catalog.check_prune_rows`), and that refusal is the
`protocol` finding. What only the language can get wrong is coverage, in two directions the pruner tolerates
silently: a file a prunable feature writes that the feature's `owned_files` do not cover stays when the feature is
pruned, and a file in a generated service carrying a marked region that `marked_files` does not list keeps the
region. A listed path that is absent is not a finding: one family's rows serve every framework of it, and the
pruner passes over a missing one by design (`prune.marked_paths`).
"""
from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import Path

from ..assets import PRUNER
from ..catalog import family_of
from ..project.backing_services import merged_layout
from ..registry import PRUNE_ROWS, READ_SIDE_FILES, WRITE_SIDE_FILES, Registry
from ..services import APPLICATIONS, FIRST_SERVICE
from .generation import Run


def owns(owned: str, destination: str) -> bool:
    """Whether a path in `owned_files` takes `destination` with it: the file itself, or a directory holding it, with
    `*` matching within one segment as the pruner's glob does."""
    have, want = owned.strip("/").split("/"), destination.strip("/").split("/")
    return len(have) <= len(want) and all(
        fnmatchcase(part, pattern) for part, pattern in zip(want[: len(have)], have, strict=True)
    )


def listed(service: Path, marked: object) -> set[Path]:
    """Every file `marked_files` names in a generated service, globs resolved the way the pruner resolves them."""
    paths: set[Path] = set()
    for relative in marked if isinstance(marked, (list, tuple)) else ():
        paths |= set(service.glob(relative)) if any(c in relative for c in "*?[") else {service / relative}
    return paths


def marked_region(path: Path) -> bool:
    try:
        return bool(PRUNER.MARKER.search(path.read_text(encoding="utf-8", errors="replace")))
    except OSError:
        return False


def row_findings(loaded: Registry, backend: str, done: list[Run]) -> list[str]:
    """Every file a prune of this backend's projects would leave behind, as its family's rows stand."""
    rows, family = loaded.answer(backend, PRUNE_ROWS), family_of(backend)
    findings: list[str] = []
    layout = merged_layout(loaded.answer(backend, WRITE_SIDE_FILES), loaded.answer(backend, READ_SIDE_FILES))
    for feature, files in layout.items():
        if feature not in PRUNER.FEATURES:
            continue  # always there, as the in-memory store is: nothing prunes it
        owned = rows["owned_files"].get(feature, ())
        findings += [
            f"backend {backend} writes {destination} for {feature}, and family {family}'s owned_files for {feature} "
            f"does not cover it, so pruning {feature} leaves it behind"
            for destination in files if not any(owns(path, destination) for path in owned)
        ]
    for run in done:
        if run.project is None:
            continue
        service = run.project / APPLICATIONS / FIRST_SERVICE
        named = listed(service, rows["marked_files"])
        findings += [
            f"backend {backend} writes {path.relative_to(service).as_posix()} with a marked region, and family "
            f"{family}'s marked_files does not list it, so pruning leaves the region in place"
            for path in sorted(service.rglob("*")) if path.is_file() and path not in named and marked_region(path)
        ]
    return list(dict.fromkeys(findings))
