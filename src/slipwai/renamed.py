"""How a member the protocol has renamed is answered, while both names are read.

A member's name is a language package's to answer, and a package is a repository of its own with a release
of its own — so renaming one is a change every language has to make, and they do not all make it in the
same week. A rename is therefore a MINOR with a window: the new name is declared, the old one stays in
`PROTOCOL` as deprecated, and an answer given under either is read, the new name first. The MINOR that
closes the window deletes the old member and makes the keel's refusal the only answer.

Kept apart from the registry, as `family_only` is, because it is a rule about answers and not about the
protocol's table: it is given the holders of one backend's answers — the backend, then its family — and
the member asked for, and it says what was answered or that nothing was. `docs/backend-protocol.md`'s
*Renamed members* names which members are in a window and which MINOR closes each.

`MISSING` rather than `None`, here and in `registry`, because presence is the test: a member answered
`None` has been answered, and the two cannot be told apart by the value alone.
"""
from __future__ import annotations

from typing import Any

#: No answer at all, which `None` is not.
MISSING = object()


def names(member: Any) -> tuple[Any, ...]:
    """The names one member's answer may be given under: its own, then the one it replaced where it has one."""
    return (member, member.was) if getattr(member, "was", None) is not None else (member,)


def held(holders: tuple[Any, ...], member: Any) -> object:
    """The first answer any holder gives to `member`, else to the name it replaced, else `MISSING`.

    Both orders matter and they are not the same order. Across holders, a backend's own answer beats its
    family's, as it does everywhere. Across names, the member's own beats the one it replaced — so a
    language that has answered both during the window is read by the name it has moved to, and a family
    that answers the old name is still overridden by a backend that answers the new one.
    """
    for name in names(member):
        for holder in holders:
            if holder is not None and name in holder.answers:
                return holder.answers[name]
    return MISSING
