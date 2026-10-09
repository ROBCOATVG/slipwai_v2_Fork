"""The shape of what a backend's entry point writes for each persistence answer, and the markers it writes with.

Each backend answers `entry_store` with an `EntryStore` on its own `LANGUAGE` object (`None` where its framework
opens its own store); this module is the type those answers are written in and the helpers that mark their
regions. Every string an answer holds is read by `wire_store` in `composition.py`, which is also where the three
rules they all follow are written down.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntryStore:
    """One transport's entry point: where it is, and what each persistence answer writes into it.

    `imports` and `open` are keyed by the feature that answered the axis — `None` for the in-memory answer,
    which owns no feature and needs no marked region because nothing can ever prune it away. `absent` is
    what the whole file reads as in a project with no event store at all, which is every project on the
    standard profile: no import, nothing opened, and `readiness()` given nothing.
    """

    entry: str
    imports: dict[str | None, str]
    open: dict[str | None, str]
    argument: str
    absent: str = ""
    #: What the entry point's own import of the HTTP adapter names, where the answer changes it. Keyed
    #: like the two above, plus `"none"` for a project that has no event store at all.
    app_imports: dict[str | None, str] | None = None
    #: And of the module holding the checked environment, for a backend whose opener is annotated with its
    #: type. Keyed the same way; an answer with no opener names nothing extra, because an import nothing
    #: uses is what a generated project's own linter refuses first.
    settings_imports: dict[str | None, str] | None = None
    #: The blank lines this language wants between what was opened and what follows it — one everywhere,
    #: two in Python, where a top-level `def` is expected to have them.
    gap: str = "\n"


#: Every answer that opens a store: the in-memory one, which owns no feature, and each feature the axis
#: offers. `"none"` — the axis never asked — is the row each backend's `entry_store` spells out on its own.
STORED: tuple[str | None, ...] = (None, "sqlite", "postgres")

#: What the marker names until `wire_store` fills it in with the key the region was found under. The
#: feature is a *key* in every mapping an answer holds and never an argument: a feature name a function is called with
#: is one line away from one a branch tests for, the defect these keyed answers exist to have stopped.
FEATURE = "__FEATURE__"


def marked(body: str, indent: str = "") -> str:
    """`body` inside its answer's marked region, so the pruner takes the two away together; `indent` is
    what a region inside a function needs, since a comment at column zero there reads as the end of it."""
    lines = "".join(f"{line}\n" for line in body.splitlines())
    return (
        f"{indent}// backing-service:{FEATURE}:begin\n{lines}"
        f"{indent}// backing-service:{FEATURE}:end\n"
    )


def hash_marked(body: str, indent: str = "") -> str:
    """The same, for a file whose comments start with `#`; `indent` is what a region inside a function
    needs, since a stray comment at column zero would close the block a reader sees."""
    lines = "".join(f"{line}\n" for line in body.splitlines())
    return (
        f"{indent}# backing-service:{FEATURE}:begin\n{lines}{indent}# backing-service:{FEATURE}:end\n"
    )


def tab_marked(body: str) -> str:
    """The same, for Go's tab-indented import block."""
    lines = "".join(f"{line}\n" for line in body.splitlines())
    return f"\t// backing-service:{FEATURE}:begin\n{lines}\t// backing-service:{FEATURE}:end\n"
