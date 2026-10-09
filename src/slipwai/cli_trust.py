"""`slipwai trust`: which publishers this machine will install from.

Three verbs, because there are three things a person does with the list: read it, add to it, and take
something off it. Adding is also what the confirm-once prompt does on the way past an install, so this is
the place to do it ahead of time — in a container image, in CI, on a machine being set up for somebody else.
"""
from __future__ import annotations

import argparse

from .assets import this_command
from .errors import GenerationError, refuse
from .trust import KEY, SAID, accept, forget, path, publishers

VERBS = ("list", "add", "remove")


def listing() -> list[str]:
    """Every accepted publisher, how it got there, and where the file is."""
    found = publishers()
    if not found:
        return ["no publisher is accepted here, so every named one is asked about once",
                f"  {path()}"]
    width = max(len(name) for name in found)
    lines = [f"  {name:<{width}}  {body.get('how', 'confirmed')}"
             + (f", {body['when']}" if body.get("when") else "")
             # A key is what makes a private channel's releases verifiable here rather than merely signed,
             # so a listing that did not say which publishers have one would not answer the question the
             # listing is read for.
             + (f", key {body[KEY][:12]}…" if body.get(KEY) else "")
             for name, body in sorted(found.items())]
    return ["publishers this machine installs from", *lines, f"  {path()}"]


def trust_main(argv: list[str]) -> None:
    prog = f"{this_command()} trust"
    parser = argparse.ArgumentParser(
        prog=prog, description="Which publishers this machine will install a package from",
        epilog="A package's publisher is asked about once, on the first install; `add` does it beforehand, "
               "which is what a container image or a CI runner needs. The four states a release can be in "
               "are: " + "; ".join(f"{name} ({said})" for name, said in SAID.items()) + ".")
    parser.add_argument("verb", choices=VERBS, nargs="?", default="list")
    parser.add_argument("publisher", nargs="?", help="who, for add and remove")
    parser.add_argument("--key", default="", metavar="<base64>",
                        help="`add` only: their Ed25519 public key, as `slipwai package key` printed it. "
                             "A private channel's releases are verified against it here; the public "
                             "channel's carry a Sigstore bundle and need none")
    parsed = parser.parse_args(argv)
    try:
        if parsed.verb == "list":
            print("\n".join(listing()))
            return
        if not parsed.publisher:
            raise GenerationError(f"`{prog} {parsed.verb} <publisher>` takes the publisher's name, as "
                                  f"`{this_command()} show <package>` prints it")
        if parsed.verb == "remove" and parsed.key:
            raise GenerationError(f"`{prog} remove` takes no key: removing a publisher takes their key "
                                  f"with them. `{prog} add {parsed.publisher} --key <base64>` replaces one")
        place = (accept(parsed.publisher, "added", parsed.key) if parsed.verb == "add"
                 else forget(parsed.publisher))
        print(f"{parsed.publisher} {'accepted' if parsed.verb == 'add' else 'removed'}; {place}")
    except GenerationError as error:
        refuse(prog, error)
