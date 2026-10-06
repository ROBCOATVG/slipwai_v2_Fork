"""The command line: `slipwai <verb>`, each verb owning its own parser.

At 2.0.0.dev0 the keel answers one question — which keel this is — so `--version` is all there is. Verbs
arrive with the modules that answer them, which is what keeps this file a dispatcher rather than somewhere
logic accumulates.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Where `VERSION` sits depends on how slipwai is being run, and there are three ways. A frozen executable
# unpacks it beside the rest of the bundle; an installed wheel carries it under the package as
# `slipwai/_bundle/`, put there by the force-include table in pyproject.toml; a checkout keeps it at the
# repository root, two directories above this file.
#
# This resolution belongs in `assets.py`, which phase 3 brings back as the one place every keel path comes
# from. It is here because `assets.py` is not back yet and the version has to be readable without it; the
# move is phase 3's, and this block goes with it.
FROZEN = bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))
BUNDLE = Path(__file__).resolve().parent / "_bundle"
if FROZEN:
    ROOT = Path(sys._MEIPASS)  # type: ignore[attr-defined]
elif BUNDLE.is_dir():
    ROOT = BUNDLE
else:
    ROOT = Path(__file__).resolve().parents[2]

VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def main() -> None:
    """`slipwai --version` prints the keel's version. With nothing to do, it prints its help and stops."""
    # What slipwai prints — its questions' arrows and dashes — is UTF-8. Windows gives a redirected stream
    # (a pipe, a CI log) its ANSI code page, cp1252, and a print there raised UnicodeEncodeError; a console
    # was fine, which is why this only ever showed up under CI.
    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        if encoding != "utf8" and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="slipwai",
        description="Slipwai's keel. Languages and extensions are packages; `slipwai search` finds them.",
    )
    parser.add_argument("--version", action="version", version=VERSION, help="print the keel's version and exit")
    # No verbs yet. Each one is registered here by the slice that brings its module back, so an unknown
    # argument is argparse's refusal rather than a stub that half-answers.
    parser.parse_args()
    parser.print_help()
