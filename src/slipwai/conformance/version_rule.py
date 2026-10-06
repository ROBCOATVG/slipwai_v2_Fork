"""The version rule AGENTS.md holds the keel to, held over one language package's directory.

A package carries its own `VERSION`, `CHANGELOG.md` and `changelog.d/`. The number its `VERSION` carries is the
smallest claim its fragments justify over its last released entry, and with no released entry it is a snapshot of
the first release, `1.0.0`. This is the suite's `version` check, and the root suite's test of every loaded package.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from ..assets import inside
from ..changelog import LEVELS, Fragment, fragments, implied
from ..versions import LONGEST_NUMBER, base, is_release, is_snapshot, key, next_snapshot
from .lines import one_line

# A released entry's heading: `## 1.4.0 — MINOR`, or `## 1.0.0` for the first, which nothing preceded.
# ASCII digits, no leading zero, and no more of them than `versions.parse` takes (`\d` is Unicode and unbounded).
NUMBER = rf"(?:0|[1-9][0-9]{{0,{LONGEST_NUMBER - 1}}})"
ENTRY = re.compile(rf"(?m)^## ({NUMBER}\.{NUMBER}\.{NUMBER})(?: — (MAJOR|MINOR|PATCH))?$")
# What a `VERSION` this keel wrote reads as: three numbers with no leading zero, and for a snapshot `.dev<N>`.
WRITTEN = re.compile(rf"{NUMBER}\.{NUMBER}\.{NUMBER}(?:\.dev{NUMBER})?")
# A fragment's prose opens with a bold sentence saying what changed.
LEAD = re.compile(r"^\*\*[^*]+[.!?]\*\*")


def problems(root: Path) -> list[str]:
    """Every way `root`'s version disagrees with its changelog, each naming the package directory and each one line."""
    try:
        found = rules(root)
    except ValueError as error:  # whatever the rule could not read is a finding, never a traceback
        return [one_line(f"{root.name if isinstance(root, Path) else root}: the version rule could not be read "
                         f"({type(error).__name__}: {error})")]
    return [one_line(finding) for finding in found]


def unreadable_or_outside(root: Path) -> list[str]:
    """The files the rule reads that are not the package's to read: resolving outside it, or a fragment directory that
    is there and cannot be listed. Nothing of the package is read until there are none."""
    name = root.name
    found = []
    for relative in ("VERSION", "CHANGELOG.md", "changelog.d"):
        try:
            inside(root, relative)
        except ValueError:
            found.append(f"{name}: {relative} resolves outside the package")
    directory = root / "changelog.d"
    if not found and os.path.lexists(directory):
        try:
            os.scandir(directory).close()
        except OSError:
            found.append(f"{name}: changelog.d is there but is not a readable directory")
    return found


def rules(root: Path) -> list[str]:
    """The rule itself, before each finding is folded to one line."""
    name = root.name
    if refused := unreadable_or_outside(root):
        return refused
    try:
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return [f"{name}: VERSION is missing; a package carries its own version (FR-032)"]
    except (OSError, UnicodeDecodeError) as error:
        return [f"{name}: VERSION cannot be read ({type(error).__name__})"]
    changelog = root / "CHANGELOG.md"
    try:
        text = changelog.read_text(encoding="utf-8") if changelog.is_file() else ""
        written: list[Fragment] = fragments(root)
    except (OSError, UnicodeDecodeError) as error:
        return [f"{name}: its changelog cannot be read ({type(error).__name__}: {error})"]
    if refused := unreadable_lines(name, text):
        return refused  # an entry such a line hides cannot be told from none, so nothing else is read of the file
    entries = [(match.group(1), match.group(2)) for match in ENTRY.finditer(text)]
    released = [entry for entry, _level in entries]
    found: list[str] = grammar(name, text, entries)
    for path, claim, body in written:
        shown = f"{name}: {path.name}"
        if claim not in LEVELS:
            found.append(f"{shown} does not open with PATCH, MINOR or MAJOR alone on a line")
        elif not LEAD.match(body):
            found.append(f"{shown} does not open with a bold sentence saying what changed")
    if not (is_release(version) or is_snapshot(version)):
        return [*found, f"{name}: VERSION is {version}, neither a release nor a snapshot"]
    if not WRITTEN.fullmatch(version):
        return [*found, f"{name}: VERSION {version} is not a version this factory could have released"]
    if is_release(version):
        return [*found, *released_rule(name, version, released, written)]
    if not released:
        if base(version) != "1.0.0":
            found.append(f"{name}: no released entry, so VERSION must be a snapshot of 1.0.0, not {version}")
        return found
    return [*found, *snapshot_rule(name, version, released, written)]


# What `str.splitlines` ends a line at besides `\n`, which `CHANGELOG.md`'s `^` and `$` do not see.
SEPARATORS = "\v\f\x1c\x1d\x1e\x85\u2028\u2029"


def unreadable_lines(name: str, text: str) -> list[str]:
    """A byte order mark, or a line separator but `\n` (CRLF is read as `\n` already): either hides an entry from the
    rule, so the first of each is named by its line."""
    found = []
    if text.startswith("\ufeff"):
        found.append(f"{name}: CHANGELOG.md line 1 starts with a byte order mark; write it as UTF-8 without one")
    for number, line in enumerate(text.split("\n"), 1):
        if any(character in SEPARATORS for character in line):
            found.append(f"{name}: CHANGELOG.md line {number} holds a line separator other than a newline; end each "
                         "line with \\n")
            break
    return found


def released_rule(name: str, version: str, released: list[str], written: list[Fragment]) -> list[str]:
    """A release `VERSION` is the newest entry, entered, with every fragment spent: what cutting a release by hand
    leaves when it is done right (D112, D118 (1))."""
    found = []
    if version not in released:
        found.append(f"{name}: VERSION {version} is a release with no ## {version} entry in CHANGELOG.md; cutting a "
                     "release writes that entry from changelog.d/")
    elif version != (newest := max(released, key=key)):
        found.append(f"{name}: VERSION {version} is already released, and the newest entry is {newest}; open "
                     f"{next_snapshot(newest)}")
    if written:
        left = ", ".join(path.name for path, _claim, _body in written)
        found.append(f"{name}: VERSION {version} is released and changelog.d/ still holds {left}; cutting a release "
                     "assembles the fragments into its entry and deletes them")
    return found


def snapshot_rule(name: str, version: str, released: list[str], written: list[Fragment]) -> list[str]:
    """A snapshot after a release: never of a spent number, never below the newest entry, and over an empty
    `changelog.d/` the PATCH a release opens; with fragments, the number they claim (D118 (1), (4))."""
    heading = base(version)
    assert heading is not None  # a snapshot, so it parses
    newest = max(released, key=key)
    opened = next_snapshot(newest)
    if heading in released:
        return [f"{name}: VERSION {version} is a snapshot of {heading}, which CHANGELOG.md already released; open "
                f"{opened}"]
    if key(heading) < key(newest):
        return [f"{name}: VERSION {version} is below the newest entry {newest}; open {opened}"]
    if not written:
        if heading != base(opened):
            return [f"{name}: VERSION {version} claims more than a PATCH over {newest} with no fragment in "
                    f"changelog.d/; a release opens {opened}, and the change that needs more raises it beside its "
                    "fragment"]
        return []
    if all(claim in LEVELS for _path, claim, _body in written):
        expected = implied(newest, written)
        if expected != heading:
            return [f"{name}: the fragments imply {expected} over {newest}, VERSION is {version}"]
    return []


def grammar(name: str, text: str, entries: list[tuple[str, str | None]]) -> list[str]:
    """`CHANGELOG.md` held to the keel's own five rules (`tests/test_changelog.py`, D118 (9)): every `## ` line an entry
    heading, newest first, none twice, every entry but the first release's naming its level, the first's none."""
    found = [
        f"{name}: CHANGELOG.md line {number}, {line.rstrip()}, is not an entry: ## <version>, or ## <version> — "
        "<LEVEL> after the first release; the file holds released entries only"
        for number, line in enumerate(text.splitlines(), 1)
        if line.startswith("## ") and not ENTRY.fullmatch(line)
    ]
    versions = [version for version, _level in entries]
    found += [f"{name}: CHANGELOG.md enters {version} twice" for version in dict.fromkeys(versions)
              if versions.count(version) > 1]
    found += [f"{name}: CHANGELOG.md's entries are not newest-first: {above} is above {below}"
              for above, below in zip(versions, versions[1:], strict=False) if key(above) < key(below)][:1]
    if entries:
        found += [f"{name}: CHANGELOG.md's entry {version} names no bump level; every entry after the first release "
                  "names one" for version, level in entries[:-1] if level is None]
        first, level = entries[-1]
        if first != "1.0.0":
            found.append(f"{name}: CHANGELOG.md's first entry is {first}; the first release is 1.0.0 (D38)")
        if level is not None:
            found.append(f"{name}: CHANGELOG.md's first entry {first} names {level}; the first release was bumped "
                         f"from nothing, so its heading is ## {first} alone (D38)")
    return found
