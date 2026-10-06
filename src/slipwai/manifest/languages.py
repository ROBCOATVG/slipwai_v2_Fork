"""The language record in `project.json`'s `generator`: which packages wrote the project, at which version.

ADR 0005: `generator.languages` maps each package that answers a generated application — a service's family
and, where it is another package, its backend's; a browser app's family, which answers the npm workspace — to that
package's `VERSION`, verbatim. A language built into the keel is not recorded, a project with nothing to record writes
`{}`, and a 1.x project has no key at all. Every writer of `generator` builds it here, so none drops the key. The
readers that hold the record to what is installed are here too: what is loaded, at which version, and which recorded
package is older than the one loaded.
"""
from __future__ import annotations

from pathlib import Path

from ..assets import VERSION, this_command
from ..catalog import PACKAGES
from ..errors import GenerationError
from ..language_directory import Package
from ..language_shape import name_fault
from ..registry import Registry, registry
from ..services import App
from ..versions import base, key, satisfies


def answered(service: App, backends: dict) -> bool:
    """Whether a service's backend is one this catalog holds: its family loaded without its framework is not."""
    try:
        return service.backend in backends
    except (GenerationError, KeyError):
        return False


def loaded_versions() -> dict[str, str]:
    """Each package the registry loaded, by name, at its `VERSION`."""
    roots = {root.resolve() for root in registry().roots.values()}
    return {package.name: package_version(package.root) for package in PACKAGES if package.root.resolve() in roots}


def refuse_older(document: dict) -> None:
    """Refuse a project recording a package at a version newer than the one loaded here (Story 4 scenario 9, D73):
    replaying it would write the tree backwards. An equal or newer version, a MAJOR included, is replayed; a recorded
    version that does not read as one cannot be called newer, and is replayed too. Then refuse a framework the project
    needs whose family is installed at a version its `requires` fails, naming the upgrade of both."""
    recorded, loaded = recorded_languages(document) or {}, loaded_versions()
    behind = [(name, version, loaded[name]) for name, version in recorded.items()
              if name in loaded and key(loaded[name]) < key(version)]
    if behind:
        said = "; ".join(f"{name} {version} recorded, {now} installed" for name, version, now in behind)
        raise GenerationError(f"this project was written by newer languages than this slipwai has ({said}): "
                              f"{this_command()} language upgrade {' '.join(name for name, *_ in behind)}")
    deployables = document.get("deployables")  # a value that is not a map is `replay`'s to refuse, as it does
    languages = {str(row.get("language")) for row in (deployables.values() if isinstance(deployables, dict) else [])
                 if isinstance(row, dict) and row.get("generated") is not False}
    needed = list(recorded) if recorded else [p.name for p in PACKAGES if p.fragment.get("family") in languages]
    pairs = broken_pairs(needed, {p.name: (p.fragment, package_version(p.root)) for p in PACKAGES if p.name in loaded})
    if pairs:
        said = "; ".join(f"{name} {version} needs {family} {wanted}, and {family} {have} is installed"
                         for name, version, family, wanted, have in pairs)
        names = " ".join(dict.fromkeys(n for name, _v, family, *_ in pairs for n in (family, name)))
        raise GenerationError(f"{said}: {this_command()} language upgrade {names}")


def broken_pairs(needed: list[str], packages: dict[str, tuple[dict, str]]) -> list[tuple[str, str, str, str, str]]:
    """Each needed framework package whose `requires` its installed family's version fails — a snapshot held as the
    release it heads for (ADR 0004) — as (name, version, family, range, family version): FR-024's framework-to-family
    check, made before anything is replayed, since the loader here does not hold a framework to its range."""
    found = []
    for name in needed:
        fragment, version = packages.get(name, ({}, ""))
        family, wanted = fragment.get("family"), (fragment.get("requires") or {}).get(fragment.get("family"))
        if family in (None, name) or family not in packages or not isinstance(wanted, str):
            continue
        have, release = packages[family][1], base(packages[family][1])
        try:
            held = release is not None and satisfies(release, wanted)
        except ValueError:
            held = False
        if not held:
            found.append((name, version, str(family), wanted, have))
    return found


def wrote_here(recorded: object, languages: dict[str, str] | None = None) -> dict:
    """The `generator` record after a command that has just written files from *this* factory's assets.

    `updatedWith` is therefore this version, whatever the project was generated by. `generatedWith` is left
    exactly as found, and written as `null` where there is nothing to find: a repository made before the
    factory recorded this says so, rather than being credited to whichever version wrote to it later.
    `languages` is the record of the packages that wrote it (ADR 0005), or None for a command that wrote no
    application's files, which carries the record as found — and leaves a 1.x project with none, so `migrate`
    still knows to derive it.
    """
    found = recorded if isinstance(recorded, dict) else {}
    kept = found.get("languages") if languages is None else languages
    return generator(found.get("generatedWith"), kept if isinstance(kept, dict) else None)


def generator(generated_with: str | None, languages: dict[str, str] | None) -> dict:
    """`generator` in the order every writer writes it. `languages` comes before `generatedWith`, which never changes,
    so that line sits between it and `updatedWith`: an `add-service` that records a package and a replay that moves
    `updatedWith` touch lines a three-way merge can tell apart, and the migration merges clean."""
    return {"name": "slipwai", **({"languages": languages} if languages is not None else {}),
            "generatedWith": generated_with, "updatedWith": VERSION}


def package_version(root: Path) -> str:
    """A package's `VERSION`, verbatim — a `.devN` kept — or `unknown` where it has none it can read."""
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip() or "unknown"
    except (OSError, UnicodeDecodeError):
        return "unknown"


def answering(apps: list[App], loaded: Registry | None = None, packages: list[Package] | None = None,
              ) -> dict[str, list[str]]:
    """Each loaded package that answers a generated application, with the applications it answers: a service's
    family and, where it is another package, its backend's; a browser app's family, which answers the npm workspace.
    A language built into the keel has the keel's root and no package, so it is not here. `loaded` and `packages` are
    the process's registry and merged packages unless a caller holds others."""
    loaded = registry() if loaded is None else loaded
    names = {package.root.resolve(): package.name for package in (PACKAGES if packages is None else packages)}
    found: dict[str, list[str]] = {}
    for app in apps:
        if not app.generated:
            continue
        for owner in dict.fromkeys([app.language, *([app.backend] if app.is_service else [])]):
            root = loaded.roots.get(owner)
            name = names.get(root.resolve()) if root is not None else None
            if name is not None:
                found.setdefault(name, []).append(app.name)
    return found


def languages_record(apps: list[App], loaded: Registry | None = None, packages: list[Package] | None = None,
                     ) -> dict[str, str]:
    """`generator.languages`: each package answering a generated application, at its `VERSION`; `{}` for none."""
    packages = PACKAGES if packages is None else packages
    roots = {package.name: package.root for package in packages}
    return {name: package_version(roots[name]) for name in sorted(answering(apps, loaded, packages))}


def unnamed(kind: str, value: object) -> str | None:
    """Why `value` is not a package name — a string the package-name rule admits — or None. The value is shown as
    Python spells it, so a control character in it is never printed raw, and cut where it is long."""
    if isinstance(value, str) and name_fault(kind, value) is None:
        return None
    shown = repr(value)
    return f"{kind} {shown if len(shown) <= 60 else shown[:57] + '...'}, which is not a package name"


def refuse_unnamed(document: dict) -> None:
    """Refuse a deployable the keel generated whose `language` is not a package name: it is read as
    a family, and as the name of a package to install, so a path, a list or a terminal escape stops here in one line.
    An application the keel did not make is in whatever language it is, and is not read."""
    deployables = document.get("deployables")
    for name, record in (deployables.items() if isinstance(deployables, dict) else []):
        if not isinstance(record, dict) or record.get("generated") is False or "language" not in record:
            continue
        if (fault := unnamed("language", record["language"])) is not None:
            raise GenerationError(f"project.json's deployable {str(name)[:40]!r} names a {fault}")


def refuse_unreadable(document: dict) -> None:
    """Refuse an adopted deployable (`generated: false`) whose `language` is not a string (D85, r25): any string is
    whatever it is and stays unread, but a list, a map, a number or `null` is not a language under any rule, and the
    toolkit hashes it as one. The same line `refuse_unnamed` says, read where the applications are built, so the
    record's own reader (`recorded_languages`) still leaves an adopted application alone."""
    deployables = document.get("deployables")
    for name, record in (deployables.items() if isinstance(deployables, dict) else []):
        if isinstance(record, dict) and record.get("generated") is False and "language" in record \
                and not isinstance(record["language"], str):
            fault = unnamed("language", record["language"])
            raise GenerationError(f"project.json's deployable {str(name)[:40]!r} names a {fault}")


def recorded_languages(document: dict) -> dict[str, str] | None:
    """The record as `project.json` holds it, or None for a project written before there was one (1.x). A name in it,
    and every generated deployable's `language`, is held to the package-name rule before anything reads it as one."""
    refuse_unnamed(document)
    generator = document.get("generator")
    found = generator.get("languages") if isinstance(generator, dict) else None
    if found is None:
        return None
    if not isinstance(found, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in found.items()):
        raise GenerationError("project.json's generator.languages is not a map from package name to version")
    for each in found:
        if (fault := unnamed("language", each)) is not None:
            raise GenerationError(f"project.json's generator.languages names a {fault}")
    return dict(found)
