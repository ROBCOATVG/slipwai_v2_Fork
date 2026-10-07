#!/usr/bin/env python3
"""Which packages the release backstop runs against: what the channel lists, not a list in a workflow.

A list written into `backstop.yml` is a list that is wrong the day somebody publishes a seventh package and
nobody remembers the file exists. So it is read from the chandlery, which is the only set a person could
actually have installed.

Prints one `GITHUB_OUTPUT` line, `packages=<json array>`. Empty where the channel cannot be reached or
lists nothing this keel can install — and the workflow refuses the release on an empty list rather than
passing, because a green that means "nothing was checked" is not a backstop.

`BACKSTOP_PACKAGES` (the workflow's `packages` input) names them instead, for running one by hand.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slipwai.catalog import CORE  # noqa: E402
from slipwai.language_directory import directory  # noqa: E402
from slipwai.language_index import Unreachable, offered, read_index, snapshots  # noqa: E402


def asked() -> list[str]:
    """The names a person named, where they named any."""
    named = os.environ.get("ASKED") or os.environ.get("BACKSTOP_PACKAGES") or ""
    return [one for one in named.replace(",", " ").split() if one]


def listed() -> tuple[list[str], str]:
    """Every package the channel offers this keel, and a line saying why where there are none."""
    try:
        found = read_index()
    except Unreachable as error:
        return [], str(error)
    names = sorted(offered(found, CORE["schemaVersion"], snapshots()))
    return names, "" if names else f"{found.name} lists nothing this keel can install"


def main() -> int:
    names = asked()
    why = ""
    if not names:
        names, why = listed()
    if why:
        print(f"backstop: {why}", file=sys.stderr)
    print(f"packages={json.dumps(names)}")
    # Where the workflow then looks for what it installed. Read from the keel rather than written into the
    # workflow, because the directory moves in 8.3 and a path in a YAML file would not move with it.
    print(f"directory={directory()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
