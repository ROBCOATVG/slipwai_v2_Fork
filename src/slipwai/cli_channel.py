"""`slipwai channel new|build|check`: running a chandlery channel, public or private.

The three things an owner of a channel does. `new` writes the repository. `build` regenerates the index from
the entry files, which is the only way the index is ever written. `check` is what a pull request is held to,
and what an owner runs before serving it.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .assets import this_command
from .channel import check
from .channel_new import write
from .errors import GenerationError, refuse
from .package_release import rebuild, settings

VERBS = ("new", "build", "check")


def channel_main(argv: list[str]) -> None:
    prog = f"{this_command()} channel"
    parser = argparse.ArgumentParser(
        prog=prog, description="Run a chandlery channel: the packages it serves, and the files it is made of",
        epilog="A channel is a directory of JSON and release files served as static files. A private one "
               "and the public one are the same shape, which is what lets the public one be checked by the "
               "code every private one runs rather than by itself.")
    parser.add_argument("verb", choices=VERBS)
    parser.add_argument("directory", nargs="?", default=".", help="the channel's directory (default: here)")
    parser.add_argument("--name", default="", metavar="<title>", help="`new` only: what the README calls it")
    parser.add_argument("--base", default="", metavar="<url>",
                        help="where this channel is served from, for its front page to show")
    parser.add_argument("--fetch", action="store_true",
                        help="`check` only: fetch each file a publisher hosts elsewhere and hold it to its "
                             "digest. What CI does; off by default so a local check waits on no download")
    parsed = parser.parse_args(argv)
    place = Path(parsed.directory).expanduser()
    try:
        if parsed.verb == "new":
            for path in write(parsed.name or place.name or "a slipwai channel", place, parsed.base):
                print(f"  {path}")
            print(f"Serve it and name its base URL in SLIPWAI_CHANDLERY. "
                  f"`{prog} check {place}` is what a pull request to it is held to")
            return
        if parsed.verb == "build":
            held = settings(place)
            written = rebuild(place, parsed.name or held.get("name", ""), parsed.base or held.get("base", ""))
            print(f"{written} and {place / 'index.html'} written from {place / 'entries'}")
            return
        findings = check(place, parsed.fetch)
    except GenerationError as error:
        refuse(prog, error)
    if findings:
        print(f"channel check: {place} does not serve what it claims to", flush=True)
        for finding in findings:
            print(f"  {finding}")
        raise SystemExit(1)
    print(f"channel check: {place} serves what it claims to")
