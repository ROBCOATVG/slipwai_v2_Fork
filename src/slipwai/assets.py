"""Where the keel's own material lives.

Every path here is resolved from this file rather than the working directory, so `slipwai` behaves the
same whichever directory it is invoked from, and an installed or frozen command reads what is bundled into
it. Nothing in the keel reads a path any other way.

Phase 1 kept this resolution in `cli.py` because there was nowhere else for it. This is that nowhere else.
The asset trees — the toolkit, the profiles, the frontends — join it in phase 3, with the code that reads
them. There are no language or extension assets to name: those live in their packages.
"""
from __future__ import annotations

import shlex
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

FROZEN = bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))
# What the wheel carries beside the package: `VERSION`, placed there by the `force-include` table in
# pyproject.toml. Absent in a checkout, where the same file sits at the repository root.
BUNDLE = Path(__file__).resolve().parent / "_bundle"
INSTALLED = BUNDLE.is_dir()
if FROZEN:
    ROOT = Path(sys._MEIPASS)  # type: ignore[attr-defined]
elif INSTALLED:
    ROOT = BUNDLE
else:
    ROOT = Path(__file__).resolve().parents[2]

# A checkout scaffolds beside itself; a command installed or frozen has no "beside", so it scaffolds where
# it is run.
DEFAULT_OUTPUT = Path.cwd() if FROZEN or INSTALLED else ROOT.parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

# The one asset tree the keel reads for itself rather than to write it into a project: the backing-service
# pruner. `PRUNER` loads it, and `axes.py` and `targets.py` hold the catalogue's tables to its, because two
# implementations of one prune would be two sets of bugs. The rest of the asset trees arrive in phase 3.
BACKING_SERVICE_ROOT = ROOT / "assets/backing-services"

# Where a package is installed to, whichever kind it is. Not `languages/`, as the experiment had it: a
# directory of that name holding `codegraph` is a small lie that costs an hour later.
PACKAGES = Path.home() / ".slipwai/packages"


def this_command(kind: str | None = None, executable: Path | None = None,
                 on_path: Callable[[str], str | None] = shutil.which, root: Path | None = None) -> str:
    """This command as the person would type it here: `slipwai` installed, the executable by its path where
    it is not the `slipwai` on the `PATH`, and a checkout's launcher by its absolute path.

    The arguments are the seam a test sets: how this copy is installed (read off `FROZEN` and `INSTALLED`
    where not given), the running executable, the lookup of `slipwai` on the `PATH`, and the checkout's
    root. A path is shell-quoted, so the command pastes and runs wherever this copy is.

    It lives here, in the tier every other may read, because every refusal that names a fix names this: a
    refusal ending in a command the reader cannot run is worse than one that ends in nothing.
    """
    if kind is None:
        kind = "executable" if FROZEN else "environment" if INSTALLED else "checkout"
    if kind == "checkout":
        return shlex.quote(str((ROOT if root is None else root) / "slipwai"))
    if kind == "executable":
        own = (Path(sys.executable) if executable is None else executable).resolve()
        found = on_path("slipwai")
        return "slipwai" if found and Path(found).resolve() == own else shlex.quote(str(own))
    return "slipwai"


def _load_pruner() -> Any:
    """The keel's own copy of the pruner a generated project gets as `scripts/backing-services.py`.

    The keel needs the same operation the project needs — cut a tree down to what was selected — and two
    implementations of one prune would be two sets of bugs, so this loads that file rather than restating
    it. This copy carries no language's rows: the checks read its features, axes and markers here, and a
    generation prunes with the same file plus every loaded family's rows from the registry.
    """
    import importlib.util

    source = BACKING_SERVICE_ROOT / "prune.py"
    spec = importlib.util.spec_from_file_location("delivery_backing_services", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load the backing-service pruner from {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRUNER = _load_pruner()
