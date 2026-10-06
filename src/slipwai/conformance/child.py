"""Run an interpreter the suite starts, and keep what it said as diagnostics only, bounded.

A package under test runs inside the probe and can print as much as it likes, to either stream, at any time. Neither
stream is ever the verdict (`run.check` reads that from a file the probe writes), so each is drained as it is
written and only its tail, `LIMIT` bytes, is kept: a package that prints 400 MiB costs the suite 64 KiB, and a pipe
that fills never stops the child. Output is decoded with `errors="replace"`, so bytes that are not UTF-8 are text
with a replacement character in it and never an exception.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import IO

from .lines import one_line

LIMIT = 64 * 1024
# The suite never writes into the package it is checking, and loading a package compiles it: so nothing here does.
QUIET = {"PYTHONDONTWRITEBYTECODE": "1"}


@dataclass(frozen=True)
class Finished:
    """How a child ended and the tail of what it printed, each stream decoded."""

    returncode: int
    stdout: str
    stderr: str

    def last_line(self) -> str:
        """The last non-empty line of stderr, else of stdout, else nothing: the one line that says what went wrong."""
        for text in (self.stderr, self.stdout):
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if lines:
                return one_line(lines[-1])
        return ""


def drain(stream: IO[bytes], limit: int = LIMIT) -> bytes:
    """Read `stream` to its end, keeping only the last `limit` bytes of it."""
    kept = b""
    while chunk := stream.read(65536):
        kept = (kept + chunk)[-limit:]
    return kept


def run(module: str, arguments: Sequence[str], env: Mapping[str, str] | None = None) -> Finished:
    """Start `python -P -m module arguments` with `env` over the caller's environment, wait for it, and return how it
    ended. `-P` keeps the working directory off the path, so a `slipwai/` in the caller's directory is not the keel."""
    process = subprocess.Popen(
        [sys.executable, "-P", "-m", module, *arguments], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, **(env or {}), **QUIET},
    )
    assert process.stdout is not None and process.stderr is not None
    tails: dict[str, bytes] = {}
    threads = [threading.Thread(target=lambda name=name, stream=stream: tails.__setitem__(name, drain(stream)))
               for name, stream in (("stdout", process.stdout), ("stderr", process.stderr))]
    for thread in threads:
        thread.start()
    try:
        returncode = process.wait()
    except BaseException:
        process.kill()  # a stop while waiting (SIGTERM as SystemExit) leaves no child writing into a directory removed
        process.wait()
        raise
    finally:
        for thread in threads:
            thread.join()
        process.stdout.close()
        process.stderr.close()
    return Finished(returncode, tails["stdout"].decode("utf-8", "replace"), tails["stderr"].decode("utf-8", "replace"))
