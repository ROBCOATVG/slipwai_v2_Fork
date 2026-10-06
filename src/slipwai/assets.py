"""Where the keel's own material lives.

Every path here is resolved from this file rather than the working directory, so `slipwai` behaves the
same whichever directory it is invoked from, and an installed or frozen command reads what is bundled into
it. Nothing in the keel reads a path any other way.

Phase 1 kept this resolution in `cli.py` because there was nowhere else for it. This is that nowhere else.
The asset trees — the toolkit, the profiles, the frontends — join it in phase 3, with the code that reads
them. There are no language or extension assets to name: those live in their packages.
"""
from __future__ import annotations

import posixpath
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


def inside(root: Path, relative: str, package: Path | None = None) -> Path:
    """`root / relative`, or a refusal where that path leaves `root`: a package reads its own `assets/` only.

    Where `package` is named, `root` is held inside it as well, once resolved: an `assets/` that is itself
    a link out of the package is the same escape as a `..`, and `root.resolve()` alone would call it home.
    """
    if package is not None and not root.resolve().is_relative_to(package.resolve()):
        raise ValueError(f"reaches outside its directory for {relative}")
    if not (root / relative).resolve().is_relative_to(root.resolve()):
        raise ValueError(f"reaches outside its directory for {relative}")
    return root / relative


def located(roots: tuple[Path, ...], relative: str, tree: bool = False) -> tuple[Path, Path] | None:
    """The first of `roots` whose `assets/<relative>` is a file (a directory for a tree), and that path;
    None where none holds it. The path is normalised first, so `<backend>/../<family>/x` is found under a
    family's root that has no `<backend>/`, and each root is still held by `inside`."""
    normal = posixpath.normpath(relative)
    for root in roots:
        try:
            path = inside(root / "assets", normal, root)
        except ValueError:
            continue
        if path.is_dir() if tree else path.is_file():
            return root, path
    return None


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
