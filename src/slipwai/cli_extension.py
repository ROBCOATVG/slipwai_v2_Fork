"""`slipwai extension list|install|remove|check` and `slipwai hooks`: the optional dev tooling, and where it attaches.

An extension is not a product-architecture choice, so it is not asked at `slipwai generate` and has no verb
under it. It is installed into the package directory beside the languages, offered by `./init`'s menu in every
project generated after that, and elected there or later with `./init --extension <key>`.

`hooks` is the other half of the same question and the one a person actually asks when something did not run:
which moments the keel fires, what each is given, and which installed extension attaches to it. It prints the
closed set whether or not anything is installed, because "there is no such point" and "nothing is attached to
it" are different answers and a list that showed only the attached ones could not tell them apart.
"""
from __future__ import annotations

import argparse

from .assets import this_command
from .catalog import REFUSALS
from .errors import GenerationError, refuse
from .extension_directory import MANIFEST
from .extension_install import catalogue, install, remove
from .extension_shape import OBLIGATIONS
from .hooks import POINTS, declared
from .language_directory import directory

VERBS = ("list", "install", "remove", "check")


def rows() -> list[str]:
    """The installed extensions, each with what the catalogue shows and the points it attaches to."""
    found = catalogue(directory())
    if not found:
        return [f"  none installed; `{this_command()} extension install <path-or-url>` adds one"]
    lines: list[str] = []
    for key, manifest in found:
        name = manifest.get("name", key)
        lines.append(f"  {key}  {name}")
        description = manifest.get("description")
        if isinstance(description, str) and description:
            lines.append(f"      {description}")
        try:
            points = ", ".join(sorted(declared(manifest)))
        except (ValueError, KeyError) as error:  # a manifest the loader already refused, said once more here
            points = f"unreadable ({error})"
        lines.append(f"      hooks: {points or 'none'}")
    return lines


def list_extensions() -> None:
    print("extensions")
    for line in rows():
        print(line)
    for line in REFUSALS:
        if line.startswith("extension "):
            print(f"  {line}")


def hooks_listing() -> list[str]:
    """Every point, what fires it, what it is given, and which installed extension attaches to it."""
    attached: dict[str, list[str]] = {}
    for key, manifest in catalogue(directory()):
        try:
            for name in declared(manifest):
                attached.setdefault(name, []).append(key)
        except (ValueError, KeyError):
            continue
    lines: list[str] = []
    for point in POINTS:
        who = ", ".join(sorted(attached.get(point.name, []))) or "nothing attached"
        lines.append(f"  {point.name}")
        lines.append(f"      fires {point.when}")
        lines.append(f"      given {', '.join(point.given)}")
        lines.append(f"      {who}")
    return lines


def hooks_main(argv: list[str]) -> None:
    """`slipwai hooks`: the closed set of points, and what is on each."""
    argparse.ArgumentParser(prog=f"{this_command()} hooks",
                            description="The moments an extension may attach to, and what is attached").parse_args(argv)
    print("hook points — a hook is reported and never fatal to the rung it runs around")
    for line in hooks_listing():
        print(line)


def check_main(path: str) -> None:
    """`slipwai extension check <dir>`: what a package would install as, and the six obligations it is held to.

    The manifest half is checked here; the obligations are checked by the conformance suite, which runs the
    entry point against a generated project. This prints them so that a publisher reading one refusal is not
    left guessing what the other five are.
    """
    from pathlib import Path

    from .catalog import CORE
    from .extension_directory import fault_in
    root = Path(path).expanduser()
    manifest, fault = fault_in(root.name, root, CORE["schemaVersion"])
    if manifest is None:
        raise GenerationError(f"{root}: {fault}")
    print(f"{root}: a readable {MANIFEST}")
    print(f"  key          {manifest['key']}  — `./init --extension {manifest['key']}`")
    print(f"  shown as     {manifest['name']}")
    print(f"  core         {manifest['core']}")
    print(f"  hooks        {', '.join(sorted(declared(manifest))) or 'none'}")
    print("  obligations, which `slipwai conformance --extension` runs:")
    for name, said in OBLIGATIONS:
        print(f"    {name:<10} {said}")


def extension_main(argv: list[str]) -> None:
    """Dispatch `slipwai extension <verb>`."""
    parser = argparse.ArgumentParser(prog=f"{this_command()} extension",
                                     description="The optional dev tooling a project may elect at `./init`")
    parser.add_argument("verb", choices=VERBS)
    parser.add_argument("arguments", nargs="*", metavar="<name-or-path>")
    parsed = parser.parse_args(argv)
    try:
        if parsed.verb == "list":
            list_extensions()
        elif parsed.verb == "install":
            for line in install(parsed.arguments, directory()):
                print(line)
            print(f"`./init --extension <key>` elects one in a project; a project generated before this "
                  f"install does not offer it until `{this_command()} migrate` is run in it")
        elif parsed.verb == "remove":
            for line in remove(parsed.arguments, directory()):
                print(line)
        else:
            if len(parsed.arguments) != 1:
                raise GenerationError(f"`{this_command()} extension check <directory>` takes one directory")
            check_main(parsed.arguments[0])
    except GenerationError as error:
        refuse(f"{this_command()} extension", error)
