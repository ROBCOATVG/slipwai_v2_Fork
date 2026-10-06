"""What this copy of slipwai can be asked for, and what to say when it cannot.

Every answer here is about installed packages: which languages the interview may offer, which
frameworks a family has, whether there is anything to write a browser app in, and the refusal for a
flag naming something absent.

They are together because they move together. Slice 4.5 brings the chandlery's index client, and each
of these gains a second half: not only what is installed but what is *installable*, so a refusal ends
on the command that installs the missing thing rather than on a list of what happens to be here. Until
then each says the true thing a keel with no index can say, and none of them pretends to know more.
"""
from __future__ import annotations

import argparse

from .catalog import CATALOG, default_language, families, framework_of, resolve_backend
from .errors import GenerationError
from .targets import offered_backends

# Four helpers the interactive menus want, and the chandlery client they really belong to is slice 4.5.
# Each is written here as the truthful answer for a keel with no index to ask: there is nothing to offer
# installing, so nothing is offered. 4.5 replaces all four with `cli_language`'s and `browser_app`'s,
# which read the index and name the command that installs what is missing.


def not_installed_languages() -> tuple[dict[str, str], str | None]:
    """What the index offers that is not installed, and why it could not be asked. No index yet, so
    neither: the menu shows what is installed and says nothing about what is not."""
    return {}, None


def not_installed_frameworks(family: str) -> dict[str, str]:
    """The same, per family."""
    del family
    return {}


def nothing_loaded() -> str:
    """Why there is no backend to generate on. Without the index client this cannot name the command
    that fixes it, so it says the one thing it does know and points at the verb that will."""
    return ("no language is installed, so there is nothing to generate on. "
            "`slipwai list` shows what this copy has; installing one is `slipwai install <name>`")


def frontend_menu() -> tuple[list[str], str, dict[str, str]]:
    """The interview's frontends. With no language answering the npm workspace there is nothing to write
    a browser app in, so only `none` is offered and the rest are shown unavailable."""
    from .npm_workspace import workspaces

    if workspaces():
        return list(CATALOG["frontends"]), CATALOG["default"]["frontend"], {}
    why = "needs a language that answers the npm workspace, and none is installed"
    return ["none"], "none", {name: why for name in CATALOG["frontends"] if name != "none"}


def undeclared_target(target: str) -> str | None:
    """`--target <t>` that no installed backend declares: the ones they do, or None with none at all."""
    if not CATALOG["backends"] or offered_backends(CATALOG, target):
        return None
    declared = [name for name in CATALOG["targets"] if offered_backends(CATALOG, name)]
    return f"--target {target} is not one any installed backend declares; they declare {', '.join(declared)}"


def no_browser(frontend: str) -> str | None:
    """`--frontend <f>` with no language installed to write a browser app in: its refusal, or None."""
    from .npm_workspace import workspaces

    if frontend == "none" or workspaces():
        return None
    return (f"--frontend {frontend} needs a language that answers the npm workspace, and none is "
            "installed. `slipwai list` shows what this copy has")


def resolve_requested_backend(args: argparse.Namespace) -> str:
    """One backend key, from either the two-step form or `--backend`.

    Both spellings are offered and mixing them is refused rather than silently resolved: `--backend
    java-spring --framework quarkus` has no reading that is not a mistake, and picking one would be
    guessing which half the caller meant.

    The refusals here say what is installed. Slice 4.5 makes them say what is *installable* too, which
    is the chandlery's to answer and needs the index client.
    """
    if args.backend is not None:
        if args.language is not None or args.framework is not None:
            raise GenerationError(
                "--backend already names the language and the framework; pass either --backend, or "
                "--language with --framework"
            )
        if args.backend not in CATALOG["backends"]:
            raise GenerationError(
                f"--backend {args.backend} is not installed; this copy has "
                f"{', '.join(CATALOG['backends']) or 'none'}"
            )
        return args.backend
    language = args.language or default_language()
    if language not in families():
        raise GenerationError(
            f"--language {language} is not installed; this copy has {', '.join(families()) or 'none'}"
        )
    offered = [framework_of(backend) for backend in families().get(language, [])]
    if args.framework is not None and args.framework not in offered:
        raise GenerationError(
            f"--framework {args.framework} is not installed for {language}; it offers "
            f"{', '.join(name for name in offered if name) or 'none'}"
        )
    return resolve_backend(language, args.framework)


def braced(names: object) -> str:
    """The `{a,b}` argparse shows for a list of choices, for a flag that checks its own value.

    Written out rather than left to `choices=`, because a language or backend that is not installed must
    be refused with the line that installs it, not with argparse's "invalid choice". The help reads the
    same either way. It lives here until `cli_language` comes back, which is where the rest of the
    language verbs' shared text is.
    """
    return "{" + ",".join(str(name) for name in names) + "}"  # type: ignore[attr-defined]
