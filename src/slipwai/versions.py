"""How this factory's version strings read: a release, or a snapshot on the way to one.

`main` never carries a released number. Between releases `VERSION` reads `1.3.0.dev0` — the release it is
working towards, with a suffix that says it is not there yet — and every green push to `main` is published
as `1.3.0.dev<N>`, `N` counting the commits since the last release. `make release` strips the suffix, tags
`v1.3.0`, and opens `1.3.1.dev0` in the next commit. So there are two shapes and this module is the one
place that reads them: what a snapshot is a snapshot *of*, which of two strings is newer, and what the next
snapshot after a release is called.

The grammar is PEP 440's, kept to the part this factory writes, because the artifact is a wheel and the
installers already agree on what `.dev` means: a pre-release, which `pip install slipwai` and `uv tool
install slipwai` pass over unless asked for. That is what lets a snapshot sit in the same registry as the
releases without ever reaching somebody who did not ask for it.
"""
from __future__ import annotations

import re

# `1.3.0`, or `1.3.0.dev4`; the pre-release segments PEP 440 also allows are read but never written.
# ASCII digits only: `\d` would also take `١` and `１`, which `int()` reads but no file this factory wrote holds.
VERSION = re.compile(r"^([0-9]+)\.([0-9]+)\.([0-9]+)(?:(a|b|rc)([0-9]+))?(?:\.dev([0-9]+))?$")
# Sorted the way PEP 440 sorts them: a dev release below every pre-release of its number, all of them below
# the release itself.
PHASE = {"dev": 0, "a": 1, "b": 2, "rc": 3, "": 4}


# Python refuses `int()` of more digits than this (4300 by default); a number this long is no version anyone wrote.
LONGEST_NUMBER = 18


def parse(version: str) -> re.Match[str] | None:
    """The match for a version this factory could have written, or None. A number of more than `LONGEST_NUMBER`
    digits is not one, so that `key`, `base` and the rest never reach `int()` with a string it would raise on."""
    text = version.strip()
    if any(len(run) > LONGEST_NUMBER for run in re.findall(r"[0-9]+", text)):
        return None
    return VERSION.match(text)


def key(version: str) -> tuple[int, ...]:
    """A version as what it sorts by, so `1.5.10` is above `1.5.9` and `1.3.0.dev4` is below `1.3.0`.

    An unreadable one sorts below every real version rather than raising: a registry may hold a file this
    factory never wrote, and a stray name is not a reason to refuse to answer.
    """
    match = parse(version)
    if match is None:
        return (0,)
    major, minor, patch, pre, pre_number, dev = match.groups()
    try:
        numbers = (int(major), int(minor), int(patch))
        int(pre_number or 0), int(dev or 0)
    except ValueError:  # past Python's digit limit for an integer: not a version anyone wrote
        return (0,)
    if dev is not None and pre is None:
        return (*numbers, PHASE["dev"], int(dev))
    if pre is not None:
        # `1.3.0rc1.dev2` is below `1.3.0rc1`; PEP 440 allows the combination even though nothing here
        # writes it.
        return (*numbers, PHASE[pre], int(pre_number), 0 if dev is None else -1, int(dev or 0))
    return (*numbers, PHASE[""], 0)


def base(version: str) -> str | None:
    """The release a version is, or is on the way to: `1.3.0` for both `1.3.0` and `1.3.0.dev4`.

    `None` for a string that is not a version at all, so a caller comparing provenance it cannot read gets
    nothing rather than a guess.
    """
    match = parse(version)
    return None if match is None else ".".join(match.groups()[:3])


def is_release(version: str) -> bool:
    """`1.3.0` and nothing else: no `.dev`, no pre-release segment."""
    match = parse(version)
    return match is not None and match.group(4) is None and match.group(6) is None


def is_snapshot(version: str) -> bool:
    """A `.dev` version: the shape `main` carries, and the only pre-release this factory publishes."""
    match = parse(version)
    return match is not None and match.group(6) is not None


def is_prerelease(version: str) -> bool:
    """Anything an installer would pass over unless told `--pre`: a snapshot, or an `a`/`b`/`rc`."""
    return parse(version) is not None and not is_release(version)


def snapshot(release: str, number: int) -> str:
    """The snapshot `number` commits past `release`'s base: `1.3.0.dev7`."""
    return f"{base(release)}.dev{number}"


def bumped(release: str, level: str) -> str:
    """`release` raised by one bump level: `1.14.2` and MINOR is `1.15.0`.

    The table in `AGENTS.md` as arithmetic, so the number `main` carries can be checked against the claims
    the changes since the last release actually make rather than taken on trust.
    """
    match = parse(release)
    if match is None:
        raise ValueError(f"{release!r} is not a version this factory could have released")
    major, minor, patch = (int(piece) for piece in match.groups()[:3])
    if level == "MAJOR":
        return f"{major + 1}.0.0"
    if level == "MINOR":
        return f"{major}.{minor + 1}.0"
    if level == "PATCH":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"{level!r} is not a bump level: MAJOR, MINOR or PATCH")


def next_snapshot(release: str) -> str:
    """What `main` opens after `release` is cut: the next PATCH, as a snapshot.

    PATCH rather than MINOR because it is the smallest claim — the first change that lands raises it to
    whatever it needs, and a claim made before any change exists is a claim about nothing.
    """
    match = parse(release)
    if match is None:
        raise ValueError(f"{release!r} is not a version this factory could have released")
    major, minor, patch = (int(piece) for piece in match.groups()[:3])
    return f"{major}.{minor}.{patch + 1}.dev0"


# A language package's `core` range: comma-joined `>=`, `<` and `==` clauses over dotted integers.
CLAUSE = re.compile(r"^(>=|<|==)(\d+(?:\.\d+)*)$")


def dotted(text: str) -> tuple[int, ...]:
    return tuple(int(piece) for piece in text.split("."))


def padded(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)), right + (0,) * (width - len(right))


def parse_range(text: str, what: str = "core") -> tuple[tuple[str, tuple[int, ...]], ...]:
    """The clauses of a range as `(operator, numbers)`; anything else raises, and never passes. `what` is the key the
    range was read from, `core` or `requires`, as the refusal names it."""
    clauses = []
    for piece in text.split(","):
        match = CLAUSE.match(piece.strip())
        if match is None:
            raise ValueError(f"{what} range {text!r} is not >=, < or == over dotted integers")
        clauses.append((match.group(1), dotted(match.group(2))))
    return tuple(clauses)


def satisfies(version: str, text: str) -> bool:
    """Whether `version` (dotted integers, `9.0`) sits inside every clause of the range `text`."""
    clauses = parse_range(text)
    if not re.fullmatch(r"\d+(?:\.\d+)*", version.strip()):
        raise ValueError(f"{version!r} is not dotted integers")
    have = dotted(version.strip())
    for operator, wanted in clauses:
        left, right = padded(have, wanted)
        if operator == ">=" and not left >= right:
            return False
        if operator == "<" and not left < right:
            return False
        if operator == "==" and left != right:
            return False
    return True


def below(version: str, text: str) -> bool:
    """Whether `version` is under a lower bound of the range `text`, rather than at or above its upper one: which way
    a version outside a range has to move (a keel behind a package's range, a family behind a framework's)."""
    for operator, wanted in parse_range(text):
        left, right = padded(dotted(version), wanted)
        if operator in (">=", "==") and left < right:
            return True
    return False
