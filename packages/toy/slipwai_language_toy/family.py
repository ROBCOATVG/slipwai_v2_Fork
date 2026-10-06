"""The `toy` family's answers: what every backend of the family shares, so a framework beside it inherits them.

A member answered here is read for every backend whose `family` is `toy` that does not answer it itself
(`Registry.answer`: the backend's own answer, else its family's). `shared_code`, `pin_files`, `makefile_variables` and
`renovate_rules` are read per family, so they belong here; the rest could live on the backend, and are here so that a
framework added beside this package (`requires: {"toy": ...}`) answers them by inheritance.
"""
from __future__ import annotations

from typing import Any

from slipwai import registry as protocol
from slipwai.project.renovate import RenovateRules
from slipwai.services import App

from .prune_rows import PRUNE_ROWS


def ci_toolchain_setup(services: list[App]) -> str:
    """The CI steps that install the toolchain before the gate runs: a real language's setup action goes here."""
    return "      - run: echo 'toy: a real language installs its toolchain here'\n"


FAMILY_ANSWERS: dict[protocol.Member[Any], object] = {
    # The `make format` recipe line, or None for a family with no formatter.
    protocol.FORMATTER: None,
    protocol.CI_TOOLCHAIN_SETUP: ci_toolchain_setup,
    # The architecture page's paragraph on code shared between services.
    protocol.SHARED_CODE: (
        "a placeholder: the toy language has no unit of sharing, and a real one says where shared code lives"
    ),
    # Files at the repository root that pin the toolchain (`.python-version`); none here.
    protocol.PIN_FILES: {},
    # The Make variables the family's recipes read, given its service paths; None where they read none.
    protocol.MAKEFILE_VARIABLES: None,
    # The Renovate managers that read this family's files, its group, and its toolchain manager; none here.
    protocol.RENOVATE_RULES: RenovateRules((), None, None),
    protocol.PRUNE_ROWS: PRUNE_ROWS,
}
