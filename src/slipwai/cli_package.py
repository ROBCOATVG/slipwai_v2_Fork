"""`slipwai package new|check|release|register`: the publisher's side of the chandlery, in one verb.

A language and an extension are both packages, found in one directory, read by one loader, built into one
shape of release file, and listed in one index. They differ in what they declare and what the keel does with
it, which is exactly the part a publisher cannot be expected to know by heart — so the verb is one verb that
works out the kind from the manifest, rather than two that would drift apart.

The four read in the order a publisher uses them. `new` writes a package that already loads. `check` runs the
conformance suite for whichever kind it is. `release` builds the file and the index entry. `register` puts
both into a channel and rebuilds its index — which for a private channel is the whole of publishing, and for
the public one is the commit a pull request carries (6.6).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .assets import this_command
from .catalog import CORE
from .errors import GenerationError, refuse
from .index_schema import EXTENSION
from .package_new import KINDS, VERBS, write
from .package_release import kind_of, register, release


def new_package(parsed: argparse.Namespace) -> None:
    written = write(parsed.kind, parsed.name, Path(parsed.into).expanduser(), CORE["schemaVersion"])
    place = Path(parsed.into) / parsed.name
    print(f"{parsed.kind} {parsed.name}:")
    for path in written:
        print(f"  {path}")
    print("Every TODO in it is a decision the keel cannot make for you. Next:")
    print(f"  {this_command()} package check {place}")


def check_package(root: Path) -> int:
    """Run whichever conformance suite this package's kind has, and return its exit status.

    Resolved first: a language's suite is given the directory holding the package and the package's own
    name — its family lives beside it, and a framework is proved against the family it requires — and `.`
    has neither a parent nor a name until it is made absolute.
    """
    from .conformance.__main__ import main as conformance
    whole = root.resolve()
    if kind_of(whole) == EXTENSION:
        return conformance(["--extension", str(whole)])
    return conformance([str(whole.parent), whole.name])


def release_package(parsed: argparse.Namespace) -> None:
    root = Path(parsed.name).expanduser()
    archive, entry_file, entry = release(root, Path(parsed.out).expanduser(), parsed.publisher)
    print(f"{entry['kind']} {root.name} {entry['version']}")
    print(f"  file          {archive}")
    print(f"  sha256        {entry['sha256']}")
    print(f"  entry         {entry_file}")
    print(f"  register it   {this_command()} package register {root} --channel <a channel checkout>")


def register_package(parsed: argparse.Namespace) -> None:
    root = Path(parsed.name).expanduser()
    channel = Path(parsed.channel).expanduser()
    archive, entry_file, index = register(root, channel, parsed.publisher)
    print(f"registered in {channel}:")
    print(f"  file          {archive.relative_to(channel)}")
    print(f"  entry         {entry_file.relative_to(channel)}")
    print(f"  index         {index.relative_to(channel)}")
    print(f"Serve {channel} and name it in SLIPWAI_CHANDLERY to install from it; "
          f"{this_command()} search lists what it holds")


def package_main(argv: list[str]) -> None:
    prog = f"{this_command()} package"
    parser = argparse.ArgumentParser(
        prog=prog, description="Write, check, build and publish a language or extension package")
    parser.add_argument("verb", choices=VERBS)
    parser.add_argument("name", help="the package's key for `new`; its directory for the others")
    parser.add_argument("--kind", choices=KINDS, default="extension",
                        help="`new` only: what the package is (default: extension). The others read the manifest")
    parser.add_argument("--into", default=".", metavar="<directory>",
                        help="`new` only: where the package directory is written (default: here)")
    parser.add_argument("--out", default="dist", metavar="<directory>",
                        help="`release` only: where the file and its entry are written (default: dist)")
    parser.add_argument("--channel", metavar="<directory>",
                        help="`register` only: a checkout of the channel to publish into")
    parser.add_argument("--publisher", default="", metavar="<identity>",
                        help="who published it, as the index records it and `slipwai show` prints it")
    parsed = parser.parse_args(argv)
    try:
        if parsed.verb == "new":
            new_package(parsed)
        elif parsed.verb == "check":
            raise SystemExit(check_package(Path(parsed.name).expanduser()))
        elif parsed.verb == "release":
            release_package(parsed)
        else:
            if not parsed.channel:
                raise GenerationError(f"`{prog} register <directory> --channel <a channel checkout>` needs "
                                      f"the channel to publish into. A private one is any directory served "
                                      f"as static files; name it in SLIPWAI_CHANDLERY to install from it")
            register_package(parsed)
    except GenerationError as error:
        refuse(prog, error)
