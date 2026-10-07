#!/usr/bin/env python3
"""Hold the release flags: declared and read, seeded off, driven both ways, and struck when they are done.

A flag is how merging and releasing become two decisions. It is also the thing every flag system in the
world accumulates and never clears, so the five rules below are about keeping the set small and honest
rather than about adding flags carefully.

1. **Declared and never read.** A key in `infra/service/flags.auto.tfvars` that no code asks for is a
   switch wired to nothing. Flipping it does nothing and nobody finds out until they flip it.
2. **Read and never declared.** Code asking for a key the infrastructure does not declare reads as *off*
   for ever — the capability is dark and no amount of flipping will reach it, because there is nothing to
   flip.
3. **Seeded anything but `off`.** A new flag seeded on is a release that happened at merge time, which is
   the one thing a flag exists to prevent.
4. **Read round the reader.** Naming `FLAG_<KEY>` at the point of use loses the single spelling, the
   transform, and the seam a test drives both paths through. Ask the reader by key.
5. **Hoisted everywhere and never struck.** This is the hygiene rule and the one that actually bites over
   time. A flag that has been on in every environment for longer than the project's own window is a code
   path kept alive for nobody, a branch every later change has to carry, and a test matrix twice the size
   it needs to be. It records when it went on, and after that it has a deadline.

Operations flags, permission flags and experiment flags are not release flags and are exempt from rule 5:
they are declared in their own section and are meant to live for ever. Only a flag a slice opened to keep
work dark is on a clock.
"""
from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[1]


ROOT = project_root(Path(__file__).resolve())
DECLARED = ROOT / "infra/service/flags.auto.tfvars"
#: Days a release flag may be on everywhere before it is overdue to be struck. Long enough to be sure, short
#: enough that nobody inherits it.
WINDOW = 30
#: `key = "off"` in the tfvars, with an optional trailing comment carrying the hoist date and the kind.
ENTRY = re.compile(r"^\s*(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*\"(?P<value>[^\"]*)\"\s*(?P<note>#.*)?$",
                   re.MULTILINE)
HOISTED = re.compile(r"hoisted[:=]?\s*(?P<when>\d{4}-\d{2}-\d{2})")
KIND = re.compile(r"kind[:=]?\s*(?P<kind>operations|permission|experiment|release)")
#: A read that goes round the reader: the variable named at the point of use.
ROUND = re.compile(r"FLAG_[A-Z][A-Z0-9_]*")
#: Where code lives. The reader itself is allowed to name the variable; it is the one place that derives it.
SOURCE = ("apps", "src", "packages", "services")
FIX = "python3 scripts/check-flags.py"


def declared() -> dict[str, dict[str, str]]:
    if not DECLARED.is_file():
        return {}
    found = {}
    for entry in ENTRY.finditer(DECLARED.read_text(encoding="utf-8")):
        note = entry.group("note") or ""
        hoisted, kind = HOISTED.search(note), KIND.search(note)
        found[entry.group("key")] = {
            "value": entry.group("value"),
            "hoisted": hoisted.group("when") if hoisted else None,
            # A flag with no kind written down is a release flag, which is the only kind on a clock. An
            # operations, permission or experiment flag says so and is exempt from the strike rule.
            "kind": kind.group("kind") if kind else "release",
        }
    return found


def code_files() -> list[Path]:
    found: list[Path] = []
    for directory in SOURCE:
        root = ROOT / directory
        if root.is_dir():
            found.extend(path for path in root.rglob("*")
                         if path.is_file() and path.suffix in {".py", ".ts", ".tsx", ".go", ".java", ".kt"})
    return found


def read_keys(text: str) -> set[str]:
    """Keys asked for through the reader, in any of the shapes the backends spell it."""
    return {found.group(1) for found in re.finditer(r"""(?:flag|isEnabled|enabled)\s*\(\s*["'](\w+)["']""",
                                                    text, re.IGNORECASE)}


def overdue(hoisted: str | None, now: datetime | None = None) -> bool:
    if not hoisted:
        return False
    try:
        when = datetime.strptime(hoisted, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        return False
    return ((now or datetime.now(UTC)) - when).days > WINDOW


def faults(now: datetime | None = None) -> list[str]:
    keys = declared()
    if not keys:
        return []
    found: list[str] = []
    asked: set[str] = set()
    where = DECLARED.relative_to(ROOT).as_posix()
    for path in code_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        asked |= read_keys(text)
        relative = path.relative_to(ROOT).as_posix()
        if "flag" in path.name.lower():
            continue  # the reader is the one place that derives the variable from the key
        for named in sorted(set(ROUND.findall(text))):
            found.append(f"{relative}: names `{named}` at the point of use. Ask the reader by key: that is "
                         f"the single spelling, the transform, and the seam a test drives both paths through")
    for key, entry in sorted(keys.items()):
        if key not in asked:
            found.append(f"{where}: `{key}` is declared and no code asks for it. A switch wired to nothing "
                         f"does nothing when it is flipped, and nobody finds out until they flip it")
        if entry["value"] != "off" and not entry["hoisted"]:
            found.append(f"{where}: `{key}` is seeded `{entry['value']}`. A new flag seeded on is a release "
                         f"that happened at merge time, which is what a flag exists to prevent")
        if entry["kind"] == "release" and overdue(entry["hoisted"], now):
            found.append(f"{where}: `{key}` has been on everywhere since {entry['hoisted']}, over the "
                         f"{WINDOW}-day window. Strike it: a flag nobody will turn off is a code path kept "
                         f"alive for nobody, and every later change carries its branch")
    for key in sorted(asked - set(keys)):
        found.append(f"{where}: `{key}` is asked for and declared nowhere, so it reads off for ever — the "
                     f"capability is dark and there is nothing to flip")
    return found


def main() -> int:
    if not DECLARED.is_file():
        print("check-flags: no flags declared yet; nothing to hold")
        return 0
    found = faults()
    if found:
        print("check-flags: the flags do not hold\n", file=sys.stderr)
        for fault in sorted(set(found)):
            print(f"  {fault}", file=sys.stderr)
        print(f"\nRun: {FIX}", file=sys.stderr)
        return 1
    print(f"check-flags: {len(declared())} flag(s) declared, read, seeded off, and inside the strike window")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
