"""Where the keel's own material lives, and the scripts it shares with what it generates.

Every path here is resolved from this file rather than the working directory, so `./slipwai generate` behaves
the same whichever directory it is invoked from, and an installed or frozen `slipwai` reads the assets bundled
into it.
"""
from __future__ import annotations

import posixpath
import shlex
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from .errors import GenerationError

FROZEN = bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))
# What the wheel carries beside the package: `assets/`, `catalog.json` and `VERSION`, placed there by the
# `force-include` table in pyproject.toml. Absent in a checkout, where the same three sit at the repository root.
BUNDLE = Path(__file__).resolve().parent / "_bundle"
INSTALLED = BUNDLE.is_dir()
if FROZEN:
    ROOT = Path(sys._MEIPASS)  # type: ignore[attr-defined]
elif INSTALLED:
    ROOT = BUNDLE
else:
    ROOT = Path(__file__).resolve().parents[2]
# A checkout scaffolds beside itself; a command installed or frozen has no "beside", so it scaffolds where it
# is run.
DEFAULT_OUTPUT = Path.cwd() if FROZEN or INSTALLED else ROOT.parent
VERSION = (ROOT / "VERSION").read_text().strip()
# Where a factory command leaves something for the project to act on and then throw away: `migrate` writes
# its catch-up notes here and `/catch-up` reads them. Spelled here, in the tier every other may read, because
# three of them need it — the module that writes the page, the `.gitignore` that keeps it out of the history,
# and the command file that tells an agent where to look.
NOTES = ".slipwai/catch-up.md"
# What slipwai last left at each path it writes and has not seen committed, by digest, so that the next answer
# `/ground` records can write over its own regeneration and still refuse a person's edit (`uncommitted.py`).
# It is this checkout's state, never a record, so it lives under `.delivery-tools/`, which every `.gitignore`
# the keel has ever written ignores — a repository adopted before this needs no new line to keep it out of
# a `git add -A`. Not inside `.git`, where it was first: Codex runs an agent's commands in a sandbox that
# makes `.git` read-only, the record was silently never written, and the second answer was refused as if a
# person had edited the first answer's files.
WRITTEN_RECORD = ".delivery-tools/written.json"
TOOLKIT_ROOT = ROOT / "assets/toolkit"
PROFILE_ROOT = ROOT / "assets/profiles"
FRONTEND_ROOT = ROOT / "assets/frontends"
BACKING_SERVICE_ROOT = ROOT / "assets/backing-services"
# Where a package is installed to, whichever kind it is. Not `languages/`, as the experiment's was: a
# directory of that name holding `codegraph` is a small lie that costs an hour later.
PACKAGES = Path.home() / ".slipwai/packages"
# What only a repository the method was installed around takes: the ratchet (brownfield adoption).
ADOPTION_ROOT = ROOT / "assets/adoption"


def inside(root: Path, relative: str, package: Path | None = None) -> Path:
    """`root / relative`, or a refusal where that path leaves `root`: a language reads its own `assets/` only.

    Where `package` is named, `root` is held inside it as well, once resolved: an `assets/` that is itself a
    link out of the package is the same escape as a `..`, and `root.resolve()` alone would call it home.
    """
    if package is not None and not root.resolve().is_relative_to(package.resolve()):
        raise ValueError(f"reaches outside its directory for {relative}")
    if not (root / relative).resolve().is_relative_to(root.resolve()):
        raise ValueError(f"reaches outside its directory for {relative}")
    return root / relative


def located(roots: tuple[Path, ...], relative: str, tree: bool = False) -> tuple[Path, Path] | None:
    """The first of `roots` whose `assets/<relative>` is a file (a directory for a tree), and that path; None where
    none holds it. The path is normalised first, so `<backend>/../<family>/x` is found under a family's root that has
    no `<backend>/`, and each root is still held by `inside`."""
    normal = posixpath.normpath(relative)
    for root in roots:
        try:
            path = inside(root / "assets", normal, root)
        except ValueError:
            continue
        if path.is_dir() if tree else path.is_file():
            return root, path
    return None


def source_text(root: Path, relative: str, package: Path | None = None) -> str:
    """The text of a language-answered source, or one line saying why it cannot be read.

    The generation-time belt behind the load-time checks: a source that leaves `root`, that is missing, or
    that is not a file (it was a file when the package loaded; a person or a tool has changed it since) is a
    `GenerationError`, never a traceback from the middle of assembling a project.
    """
    try:
        path = inside(root, relative, package)
    except ValueError as error:
        raise GenerationError(f"{error}") from error
    if not path.exists():
        raise GenerationError(f"{relative} is missing under {root}")
    if not path.is_file():
        raise GenerationError(f"{relative} is not a file under {root}")
    return path.read_text()


def contained(destination: Path, relative: str) -> Path:
    """`destination / relative`, or a refusal where that path resolves outside `destination`.

    Generation never writes outside the directory it was given: a path a language answered with `..` in it, or
    an absolute one, would otherwise land wherever it said.
    """
    path = destination / relative
    if not path.resolve().is_relative_to(destination.resolve()):
        raise GenerationError(f"refusing to write {relative}: it resolves outside {destination}")
    return path


def asset_tree(root: Path, within: Path | None = None) -> dict[str, str]:
    """Every file under an asset directory, keyed by its path relative to that directory.

    The asset directories that hold a *tree* of files — a language's walking skeleton, the frontend app —
    are laid out at the paths the files land on, so reading one is a copy and nothing else. That is what
    makes adding a file to a skeleton an edit under `assets/` with no code change anywhere: there is no
    list of filenames to also remember.

    Read with `newline=""` so the string holds whatever line endings the file on disk holds, and
    `write_project` writes it back the same way. Universal-newline translation would be invisible for the
    whole of `assets/` bar one file and silently wrong for that one: `mvnw.cmd` is CRLF throughout, and it
    is a batch/PowerShell polyglot that re-reads itself with `Get-Content -Raw`, so flattening it is not a
    cosmetic difference. A pipeline that is faithful to the bytes needs no exception for it.

    Every file is held, once its links are resolved, inside `within` — the tree itself unless a caller names a
    wider one, a language's root — and one that is not refuses the whole copy: a link in a package's tree must
    not carry a file from anywhere else into a project.
    """
    bound = (root if within is None else within).resolve()
    files = asset_files(root)
    for path in files:
        if not path.resolve().is_relative_to(bound):
            raise GenerationError(f"{path.relative_to(root).as_posix()} under {root} links to a file outside {bound}")
    return {path.relative_to(root).as_posix(): read_faithfully(path) for path in files}


def asset_files(root: Path) -> list[Path]:
    """Every file under an asset directory, in path order, leaving the interpreter's caches out.

    A script under `assets/` that Python has imported or compiled leaves a `__pycache__` beside it — a test
    that imported the pruner, or `pip` byte-compiling the bundle when the package is installed — and a
    `.pyc` read as text is a UnicodeDecodeError on the first project. The one walker every reader of the
    tree goes through is where that is excluded, so no reader has to remember to.
    """
    return sorted(
        path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts
    )


def read_faithfully(path: Path) -> str:
    """The file's text with its own line endings — `read_text(newline="")`, spelled for Python 3.11.

    `Path.read_text` only grew a `newline` parameter in 3.13; on the 3.11 the README promises it raises
    `TypeError` before the first asset is read. `open` has taken `newline` all along.
    """
    with path.open(newline="") as handle:
        return handle.read()


def _load_pruner():
    """The generated project's own prune script, imported rather than reimplemented.

    `assets/backing-services/prune.py` is emitted as `scripts/backing-services.py` so a project can prune
    its backing services at `./init` time. The keel needs the same operation to cut a generated project
    down to what was selected here, and two implementations of one prune would be two sets of bugs — so
    this loads that file. This is the keel's copy, with no language's rows: the checks read its features, axes
    and markers here, and the keel prunes with `project.pruner.pruner()`, the same file with every loaded
    family's rows from the registry.
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




def this_command(kind: str | None = None, executable: Path | None = None,
                 on_path: Callable[[str], str | None] = shutil.which, root: Path | None = None) -> str:
    """This command as the person would type it here: `slipwai` installed, the executable by its path where it is
    not the `slipwai` on the `PATH`, and a checkout's launcher by its absolute path. The arguments are the seam a test
    sets: how this copy is installed (`upgrade.how_installed`'s words; read off `FROZEN` and `INSTALLED` where not
    given), the running executable, the lookup of `slipwai` on the `PATH` and the checkout's root. A path is
    shell-quoted, so the command pastes and runs wherever this copy is. Here, in the tier every other may
    read, because every refusal for a missing language names it — the manifest's as well as the verbs'."""
    if kind is None:
        kind = "executable" if FROZEN else "environment" if INSTALLED else "checkout"
    if kind == "checkout":
        return shlex.quote(str((ROOT if root is None else root) / "slipwai"))
    if kind == "executable":
        own = (Path(sys.executable) if executable is None else executable).resolve()
        found = on_path("slipwai")
        return "slipwai" if found and Path(found).resolve() == own else shlex.quote(str(own))
    return "slipwai"


# What an isolated child runs: the package's own parent directory — the one this copy was loaded from, not one the
# current directory or `PYTHONPATH` names — put first, then the CLI. It is the first argument, taken off before the
# verb's own arguments are parsed.
_BOOT = "import sys; sys.path.insert(0, sys.argv.pop(1)); from slipwai.cli import main; main()"


def relaunch() -> list[str]:
    """This command as a child process starts it, run as this copy and no other: the executable itself where frozen
    (the bootloader reads no `PYTHONPATH` and has no current directory on its path), else this interpreter in
    isolated mode — `-I`, which implies `-E` (no `PYTHON*` variables), `-s` and safe-path (no current directory or
    script directory first on `sys.path`, `python -I --help`) — loading the package from where this copy lives. For a
    verb that has just installed or replaced something this process loaded too early to see (`migrate`, FR-039;
    `upgrade`'s language step)."""
    if FROZEN:
        return [sys.executable]
    return [sys.executable, "-I", "-c", _BOOT, str(Path(__file__).resolve().parent.parent)]
