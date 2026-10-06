"""`slipwai search` and `slipwai show`: browsing the chandlery from the command line.

A person who wants a language has to find out it exists before they can install it, and version 1 had
no way to ask: `list` says what is installed and what the index happens to offer, in one shape, with no
way to narrow it. These two are the answer to "what is there?" and "what is this one?".

Both read the same index `install` reads, so what `search` shows is what `install` would fetch. Neither
needs a package installed, and neither installs anything.

Every line says whether a package is installed, because the first thing a reader does with a search
result is work out whether they already have it.
"""
from __future__ import annotations

import argparse

from .assets import this_command
from .catalog import families
from .language_directory import directory
from .language_index import Index, Release
from .language_install import installed
from .versions import key


def latest(releases: list[Release]) -> Release | None:
    """The newest release of one package, by version. None for a name the index lists with none."""
    return max(releases, key=lambda release: key(release.version), default=None)


def haystack(release: Release) -> str:
    """Everything about a release a search term may match: its name, what it says about itself, the
    family it belongs to, the frameworks it carries and the axis options it answers.

    A reader searching for "postgres" means "something that will talk to Postgres for me", and the
    thing that knows is the option the package answers — not its name, which is the language's.
    """
    fragment = release.fragment
    parts = [release.name, str(fragment.get("description", "")), str(fragment.get("family", ""))]
    for key_, row in (fragment.get("backends") or {}).items():
        parts += [key_, str(row.get("label", "")), str(row.get("framework", ""))]
        for axis, options in (row.get("options") or {}).items():
            parts += [axis, *(str(option) for option in options)]
    parts += [str(tag) for tag in (fragment.get("tags") or [])]
    return " ".join(parts).lower()


def here() -> set[str]:
    """Every package name this copy already has, installed or loaded."""
    return {*families(), *installed(directory())}


def status(name: str, have: set[str]) -> str:
    return "installed" if name in have else "available"


def matches(found: Index, term: str, kind: str | None = None, family: str | None = None) -> list[Release]:
    """The newest release of each package the term matches, narrowed by kind and family, by name."""
    rows: list[Release] = []
    for _, releases in sorted(found.releases.items()):
        release = latest(releases)
        if release is None:
            continue
        if term and term.lower() not in haystack(release):
            continue
        if family is not None and release.fragment.get("family") != family:
            continue
        if kind is not None and str(release.fragment.get("kind", "language")) != kind:
            continue
        rows.append(release)
    return rows


def search_lines(found: Index | None, unreachable: list[str], term: str,
                 kind: str | None = None, family: str | None = None) -> list[str]:
    """What `search` prints: one line per package, or why nothing could be asked."""
    if found is None:
        return [*(line.strip() for line in unreachable),
                f"{this_command()} list shows what is installed"]
    rows = matches(found, term, kind, family)
    if not rows:
        asked = f" matching {term!r}" if term else ""
        return [f"no package{asked} in {found.name}"]
    have = here()
    width = max(len(release.name) for release in rows)
    return [
        f"  {release.name:<{width}}  {release.version:<12}  {status(release.name, have):<9}  "
        f"{release.fragment.get('description', '') or describe(release)}"
        for release in rows
    ]


def describe(release: Release) -> str:
    """A line for a package that declares no description: what it offers, which is better than nothing."""
    backends = list(release.fragment.get("backends") or {})
    return f"backends: {', '.join(backends)}" if backends else "no description"


def show_lines(found: Index | None, unreachable: list[str], name: str) -> list[str]:
    """What `show` prints for one package: everything the index knows, and how to install it."""
    if found is None:
        return [*(line.strip() for line in unreachable)]
    releases = found.releases.get(name)
    if not releases:
        return [f"{name} is not in {found.name}. {this_command()} search lists what is"]
    release = latest(releases)
    assert release is not None
    fragment = release.fragment
    lines = [f"{release.name} {release.version}  ({status(release.name, here())})"]
    if fragment.get("description"):
        lines.append(f"  {fragment['description']}")
    lines.append(f"  family        {fragment.get('family', release.name)}")
    lines.append(f"  speaks keel   {fragment.get('core', 'unstated')}")
    for backend, row in (fragment.get("backends") or {}).items():
        lines.append(f"  backend       {backend}  {row.get('label', '')}")
        for axis, options in sorted((row.get("options") or {}).items()):
            lines.append(f"      {axis:<12} {', '.join(str(option) for option in options)}")
        if row.get("targets"):
            lines.append(f"      {'targets':<12} {', '.join(str(target) for target in row['targets'])}")
    lines.append(f"  releases      {', '.join(r.version for r in sorted(releases, key=lambda r: key(r.version)))}")
    lines.append(f"  install       {this_command()} language install {release.name}")
    return lines


def search_main(argv: list[str]) -> None:
    from .cli_language import reach, snapshots

    parser = argparse.ArgumentParser(
        prog="slipwai search",
        description="Find a language or an extension in the chandlery",
        epilog="A term matches a package's name, its description, its family, its backends and the axis "
        "options it answers — so `search postgres` finds whatever will talk to Postgres for you, "
        "whichever language it is written in. With no term, everything is listed.",
    )
    parser.add_argument("term", nargs="?", default="", help="what to look for")
    parser.add_argument("--kind", choices=("language", "extension"), default=None)
    parser.add_argument("--family", default=None, help="only packages of this language family")
    parser.add_argument("--pre", action="store_true", help="count snapshots in the index")
    args = parser.parse_args(argv)
    found, _, unreachable = reach(snapshots(args.pre))
    print("\n".join(search_lines(found, unreachable, args.term, args.kind, args.family)))


def show_main(argv: list[str]) -> None:
    from .cli_language import reach, snapshots

    parser = argparse.ArgumentParser(
        prog="slipwai show", description="Everything the chandlery knows about one package")
    parser.add_argument("name", help="the package's name")
    parser.add_argument("--pre", action="store_true", help="count snapshots in the index")
    args = parser.parse_args(argv)
    found, _, unreachable = reach(snapshots(args.pre))
    print("\n".join(show_lines(found, unreachable, args.name)))
