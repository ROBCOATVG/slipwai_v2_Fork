"""Which backends answer a family-only field differently from their family's reference.

The keel reads a few answers once per family, from the family's first service (`registry.FAMILY_ONLY`), so a framework
answering one differently would be heard or ignored by service order. This is the comparison `registry.load` refuses
it by, kept apart from the registry and importing nothing of it: it is given each family's answers and its backends',
keyed by member name, and returns one line per backend and reference, naming every differing field and the fix.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MethodType
from typing import Any

ABSENT = object()
# Of `tooling`, and of each `feature_tooling` entry, only these are read once per family.
TOOLING_FIELDS = ("ci_image", "container_setup")
Answers = Mapping[str, object]
# A family's own answers, its own package's backends' and the other packages' frameworks', each keyed by backend.
Family = tuple[Answers, Mapping[str, Answers], Mapping[str, Answers]]
Differs = dict[tuple[str, str, str, "str | None"], list[str]]


def _n(name: object) -> str:
    """A name as a refusal shows it, the registry's way: bare, unless a character would break the line."""
    text = str(name)
    return text if text.isprintable() else repr(text)


def fields(member: str, value: object) -> dict[str, object]:
    """The family-only fields of one answer, by the name a refusal shows: `repository_files`, `tooling.ci_image`,
    `feature_tooling.<feature>.ci_image`. An answer of the wrong kind has none here; `load` names its kind."""
    if member == "tooling":
        return {f"tooling.{f}": value.get(f, ABSENT) for f in TOOLING_FIELDS} if isinstance(value, Mapping) else {}
    if member == "feature_tooling":
        if not isinstance(value, Mapping):
            return {}
        return {f"feature_tooling.{feature}.{f}": entry[f] for feature, entry in value.items()
                if isinstance(entry, Mapping) for f in TOOLING_FIELDS if f in entry}
    return {member: value}


def same(left: object, right: object) -> bool:
    """A callable by identity — a framework may inherit or re-export its family's function, never replace it — and
    anything else by value. A bound method is made anew on each access, so two are one function where they hold the same
    function of the same object."""
    if left is right:
        return True
    if isinstance(left, MethodType) and isinstance(right, MethodType):
        return left.__func__ is right.__func__ and left.__self__ is right.__self__
    if callable(left) or callable(right):
        return False
    try:
        return bool(left == right)
    except Exception:  # noqa: BLE001 - an answer whose comparison raises is not the same answer
        return False


def differing(left: Mapping[str, object], right: Mapping[str, object]) -> list[str]:
    """The fields two backends answer differently, absent on one side included, in the order they were read."""
    names = dict.fromkeys([*left, *right])
    return [name for name in names if not same(left.get(name, ABSENT), right.get(name, ABSENT))]


def listed(names: list[str]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def effective(answers: Answers, family: Answers, member: str) -> dict[str, object]:
    """A backend's family-only fields of `member`: its own answer's, else its family's."""
    answer = answers.get(member, family.get(member, ABSENT))
    return {} if answer is ABSENT else fields(member, answer)


def compare(name: str, family: Family, member: str, groups: Differs) -> None:
    """Add to `groups` each backend of family `name` whose `member` fields differ from the reference: the family's own
    answer, which its own package's backends are held to as the frameworks are; else its own package's backends', where
    they agree; else, with none there, the frameworks pairwise. Its own package's backends that disagree, the family
    not answering, are each named."""
    answers, own, others = family

    def differs(key: str, kind: str, other: str | None, names: list[str]) -> None:
        if names:
            groups.setdefault((key, name, kind, other), []).extend(names)

    def pairwise(kind: str, values: Mapping[str, dict[str, object]]) -> None:
        for key, found in values.items():
            for other, compared in values.items():
                if other != key:
                    differs(key, kind, other, differing(found, compared))

    mine = {key: effective(backend, answers, member) for key, backend in own.items()}
    shown: str | None = None
    if member in answers:
        reference = fields(member, answers[member])
        for key, found in mine.items():  # the family's own package is held to its answer, as a framework is
            differs(key, "family", None, differing(found, reference))
    elif mine:
        pairwise("own", mine)
        reference = next(iter(mine.values()))
        if any(differing(found, reference) for found in mine.values()):
            return  # its own package disagrees with itself, which is its fault and is said above
        shown = ", ".join(mine)
    else:
        pairwise("pair", {key: effective(backend, answers, member) for key, backend in others.items()})
        return
    for key, backend in others.items():
        differs(key, "family", shown, differing(effective(backend, answers, member), reference))


def line(key: str, family: str, kind: str, other: str | None, names: list[str]) -> str:
    """The one line for a backend and what it differs from, naming the fields and the fix."""
    it = "it" if len(names) == 1 else "them"
    said = f"backend {_n(key)} answers {listed(names)} differently from "
    once = f"the keel reads {it} once per family"
    if kind == "family":
        seen = "" if other is None else f" (backend{'s' if ', ' in other else ''} {other})"
        return said + f"family {_n(family)}{seen}; {once} — leave {it} unanswered to inherit the family's"
    fix = f"{once} — answer {it} once, on family {_n(family)}"
    if kind == "own":
        return said + f"backend {_n(other)}, both of family {_n(family)}'s own package; {fix}"
    return said + f"backend {_n(other)}, both frameworks of family {_n(family)}, which does not answer {it}; {fix}"


def refusals(families: Mapping[str, Any], backends: Mapping[str, Any], claimed: Mapping[str, int],
             origin: Mapping[str, int], members: Sequence[str]) -> list[str]:
    """A line for each backend answering one of `members` differently from its family's reference. `families` and
    `backends` are the registry's, their answers readable; `claimed` is the language declaring each family (its claim,
    C004, D45) and `origin` the one declaring each backend, so a family's own package is told from its frameworks."""

    def named(answers: Mapping[Any, object]) -> dict[str, object]:
        return {str(m.name): value for m, value in answers.items() if getattr(m, "name", None) in members}

    groups: Differs = {}
    for name, family in families.items():
        mine = {k: b for k, b in backends.items() if b.family == name}
        held: Family = (named(family.answers),
                        {k: named(b.answers) for k, b in mine.items() if origin.get(k) == claimed.get(name)},
                        {k: named(b.answers) for k, b in mine.items() if origin.get(k) != claimed.get(name)})
        for member in members:
            compare(name, held, member, groups)
    return [line(key, family, kind, other, names) for (key, family, kind, other), names in groups.items()]
