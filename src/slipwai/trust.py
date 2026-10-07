"""Who this machine will install a package from, and what it knows about how a release was signed.

Installing a package is running somebody else's code: a language's Python is imported into the keel, and an
extension's entry point edits the project. The digest the index publishes proves the file is the file the
index listed; it says nothing about who listed it. So the question this answers is the other one — *whose
package is this, and have I agreed to that before?*

**Confirm once, then never again.** A publisher a person has accepted is written to `~/.slipwai/trust.json`
and every later release of theirs installs silently. A prompt on every install is a prompt nobody reads, and
one that cannot be answered in CI is a prompt that turns into `--yes` in a script.

**`ROBCOATVG` is seeded.** The keel's own publisher, in the file the first time it is written. Not special-
cased in the code: it is a row like any other and can be removed, which is the difference between a default
and a rule.

**Four states, and they are not three.** A release is `verified` where a signature was checked and matched;
`unverified` where one is carried and this copy has no verifier for it; `unsigned` where the index carries
none; and `untrusted` where the publisher is not one this machine has accepted. They are kept apart because
a person acts differently on each, and a listing that collapsed the middle two would say "signed" about a
signature nobody looked at — which is the one thing a signature must never be used to say.

Which verifier fills `verified` is the fork recorded in the plan (6.5): Python's standard library has no
X.509 and no ECDSA, so a Sigstore bundle cannot be checked by a keel that ships with no dependencies. This
module is everything that does not depend on the answer, and `check_signature` is the one seam that does.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from .errors import GenerationError

STORE = "trust.json"
#: Seeded the first time the file is written. A row like any other: removing it is allowed and means it.
SEEDED = ("ROBCOATVG",)
VERIFIED, UNVERIFIED, UNSIGNED, UNTRUSTED = "verified", "unverified", "unsigned", "untrusted"
#: What each state means in a listing, in one phrase, so every command says it the same way.
SAID = {
    VERIFIED: "signature checked",
    UNVERIFIED: "signed, and this copy has no verifier for it",
    UNSIGNED: "the index carries no signature",
    UNTRUSTED: "from a publisher this machine has not accepted",
}


def home() -> Path:
    """Where the trust store lives. `SLIPWAI_HOME` moves it, which is how the suite keeps off a person's."""
    named = os.environ.get("SLIPWAI_HOME")
    return Path(named) if named else Path.home() / ".slipwai"


def path() -> Path:
    return home() / STORE


def read() -> dict:
    """The store, or the seeded one where there is none. A store that cannot be parsed is a refusal.

    Refused rather than replaced: this file is the record of what a person agreed to, and quietly starting
    again from the seed would silently drop every publisher they had accepted.
    """
    place = path()
    if not place.is_file():
        return {"v": 1, "publishers": {name: {"how": "seeded"} for name in SEEDED}}
    try:
        held = json.loads(place.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as error:
        raise GenerationError(f"{place} cannot be read ({error}), and it is the record of which publishers "
                              f"you have accepted. Fix it or move it aside; a new one is written with "
                              f"{', '.join(SEEDED)} in it") from None
    if not isinstance(held, dict) or not isinstance(held.get("publishers"), dict):
        raise GenerationError(f"{place} is not a trust store. Move it aside and one is written fresh")
    return held


def publishers() -> dict[str, dict]:
    """Every publisher this machine has accepted, and what it knows about each."""
    return dict(read()["publishers"])


def trusted(publisher: str) -> bool:
    """Whether this publisher has been accepted here. An unnamed publisher is never one."""
    return bool(publisher) and publisher in publishers()


def accept(publisher: str, how: str = "confirmed") -> Path:
    """Record a publisher as accepted, and return where it was written."""
    if not publisher:
        raise GenerationError("a publisher with no name cannot be accepted: the index names none for this "
                              "package, so there is nothing to agree to")
    held = read()
    held["publishers"][publisher] = {"how": how, "when": datetime.now(UTC).strftime("%Y-%m-%d")}
    place = path()
    place.parent.mkdir(parents=True, exist_ok=True)
    place.write_text(json.dumps(held, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return place


def forget(publisher: str) -> Path:
    """Take a publisher out again. Their installed packages stay; their next release asks again."""
    held = read()
    if publisher not in held["publishers"]:
        raise GenerationError(f"{publisher} is not an accepted publisher; accepted: "
                              f"{', '.join(sorted(held['publishers'])) or 'none'}")
    del held["publishers"][publisher]
    place = path()
    place.parent.mkdir(parents=True, exist_ok=True)
    place.write_text(json.dumps(held, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return place


def check_signature(publisher: str, signature: str, data: bytes) -> bool | None:
    """Whether the signature is this publisher's over these bytes. `None` where this copy cannot say.

    The seam. `None` is not `False`: "I checked and it is wrong" and "I have no way to check" are different
    answers, and a client that returned `False` for the second would refuse every signed package on every
    machine without a verifier — which is how a security feature becomes the thing people turn off.
    """
    return None


def state_of(publisher: str, signature: str, data: bytes | None = None) -> str:
    """Which of the four states this release is in for this machine.

    An index that names no publisher is `unsigned`, not `untrusted`: there is nobody to have accepted, and a
    signature nobody claims proves nothing anyway. A `file:` channel on a person's own machine names none,
    and so does every index published before the field existed.
    """
    if not publisher:
        return UNSIGNED
    if not trusted(publisher):
        return UNTRUSTED
    if not signature:
        return UNSIGNED
    if data is None:
        return UNVERIFIED
    found = check_signature(publisher, signature, data)
    if found is None:
        return UNVERIFIED
    if not found:
        raise GenerationError(f"the signature {publisher} published for this release does not match the file "
                              f"the channel served. Refusing to install it; tell {publisher} and the channel")
    return VERIFIED


def admitted(name: str, publisher: str, signature: str, data: bytes | None = None,
             confirm: bool = False) -> str:
    """The state, or a refusal naming what to do. `confirm` accepts an unaccepted publisher on the way past.

    An unnamed publisher is not refused: a `file:` channel somebody runs on their own machine, and every
    index published before the field existed, name none. What is refused is a *named* publisher this machine
    has not agreed to, because that is the one case where there is something to agree to.
    """
    if publisher and not trusted(publisher):
        if not confirm:
            raise GenerationError(
                f"{name} is published by {publisher}, which this machine has not accepted. Accept them "
                f"once and every later release installs silently: pass --accept-publisher, or "
                f"`slipwai trust add {publisher}`")
        accept(publisher)
    return state_of(publisher, signature, data)
