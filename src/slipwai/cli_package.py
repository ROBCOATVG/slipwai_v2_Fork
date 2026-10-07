"""`slipwai package new`: the publisher's side of the chandlery, in one verb.

A language and an extension are both packages, found in one directory, read by one loader, and published to
one index. They differ in what they declare and what the keel does with it, which is exactly the part a
publisher cannot be expected to know by heart — so the verb is one verb with a `--kind`, rather than two that
would drift apart.

`new` is the whole of it for now. `check`, `release` and `register` arrive with the slices that give the
chandlery an index to register into; `extension check` already reads a package in place, which is what a
publisher needs before any of that exists.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .assets import this_command
from .catalog import CORE
from .errors import GenerationError, refuse
from .package_new import KINDS, write

VERBS = ("new",)


def package_main(argv: list[str]) -> None:
    prog = f"{this_command()} package"
    parser = argparse.ArgumentParser(
        prog=prog, description="Write a language or extension package this keel loads on the first try")
    parser.add_argument("verb", choices=VERBS)
    parser.add_argument("name", help="the package's key: lower case, letters, digits and single dashes")
    parser.add_argument("--kind", choices=KINDS, default="extension",
                        help="what the package is (default: extension)")
    parser.add_argument("--into", default=".", metavar="<directory>",
                        help="where the package directory is written (default: here)")
    parsed = parser.parse_args(argv)
    try:
        written = write(parsed.kind, parsed.name, Path(parsed.into).expanduser(), CORE["schemaVersion"])
    except GenerationError as error:
        refuse(prog, error)
    print(f"{parsed.kind} {parsed.name}:")
    for path in written:
        print(f"  {path}")
    nexts = (f"  {this_command()} extension check {Path(parsed.into) / parsed.name}"
             if parsed.kind == "extension"
             else f"  {this_command()} language install {Path(parsed.into) / parsed.name}")
    print("Every TODO in it is a decision the keel cannot make for you. Next:")
    print(nexts)
