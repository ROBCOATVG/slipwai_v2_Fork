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

**Two verifiers, by role** (plan 6.5, decided 2026-10-08). Python's standard library has no X.509 and no
ECDSA, so a Sigstore bundle cannot be checked by a keel that ships with no dependencies — but Ed25519 is
ninety lines of arithmetic, which `ed25519.py` is. So a private channel signs with a key its organisation
holds, which is the normal arrangement there and where the keyless argument does not apply, and every
machine verifies it end to end. The public channel signs keyless from CI, and a machine that installed
`slipwai[verify]` verifies the bundle through the real library; one that did not keeps the digest, TLS to
the channel and the identity the channel's own CI recorded, and says `unverified` — which is the honest
word for it, and is why `None` exists.

**A signature says which scheme it is.** `ed25519:<base64>` is the one this keel checks itself; anything
else is read as a Sigstore bundle. The scheme travels with the signature rather than being inferred from
the channel, because the client would otherwise have to be told which channel an entry came from in order
to know what it is looking at — and a verifier that guesses is a verifier that can be made to guess wrong.
Nothing is downgraded by it either: an `ed25519:` signature only reaches `verified` where the publisher is
accepted *and* this machine holds their key, and a signature with no key behind it is `unverified`.
"""
from __future__ import annotations

import base64
import binascii
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from . import ed25519
from .assets import this_command
from .errors import GenerationError

STORE = "trust.json"
#: Seeded the first time the file is written. A row like any other: removing it is allowed and means it.
SEEDED = ("ROBCOATVG",)
#: How an Ed25519 signature says so. Everything without it is read as a Sigstore bundle.
ED25519 = "ed25519:"
#: What a publisher's row calls their public key, base64, where this machine holds one.
KEY = "key"
#: The import that verifies a Sigstore bundle, where `pip install slipwai[verify]` put it there.
EXTRA = "slipwai[verify]"
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


def accept(publisher: str, how: str = "confirmed", key: str = "") -> Path:
    """Record a publisher as accepted, and return where it was written.

    `key` is their Ed25519 public key, base64, which is what makes a private channel's releases verifiable
    on this machine rather than merely signed. Accepting without one is the ordinary case and says so: the
    public channel's releases carry a Sigstore bundle and no key belongs here for them.
    """
    if not publisher:
        raise GenerationError("a publisher with no name cannot be accepted: the index names none for this "
                              "package, so there is nothing to agree to")
    if key and public_key(key) is None:
        raise GenerationError(f"{key!r} is not an Ed25519 public key: {ed25519.KEY_BYTES} bytes, base64, as "
                              f"`{this_command()} package key` prints it")
    held = read()
    held["publishers"][publisher] = {"how": how, "when": datetime.now(UTC).strftime("%Y-%m-%d"),
                                     **({KEY: key} if key else {})}
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


def decoded(text: str) -> bytes | None:
    """Base64 as bytes, or None where it is not base64 — which a signature field a stranger wrote may not be."""
    try:
        return base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        return None


def public_key(text: str) -> bytes | None:
    """A publisher's key as bytes, or None where it is not one. Length is the whole of what makes it a key."""
    found = decoded(text)
    return found if found is not None and len(found) == ed25519.KEY_BYTES else None


def key_of(publisher: str) -> bytes | None:
    """The Ed25519 public key this machine holds for a publisher, or None where it holds none."""
    row = publishers().get(publisher) or {}
    return public_key(str(row.get(KEY, "")))


def check_signature(publisher: str, signature: str, data: bytes) -> bool | None:
    """Whether the signature is this publisher's over these bytes. `None` where this copy cannot say.

    The seam, and both sides of it. `None` is not `False`: "I checked and it is wrong" and "I have no way
    to check" are different answers, and a client that returned `False` for the second would refuse every
    signed package on every machine without a verifier — which is how a security feature becomes the thing
    people turn off. So a missing key and a missing extra are both `None`, and only arithmetic that ran and
    disagreed is `False`.
    """
    if signature.startswith(ED25519):
        key, raw = key_of(publisher), decoded(signature[len(ED25519):])
        if key is None or raw is None:
            return None
        return ed25519.verify(key, data, raw)
    return sigstore_checked(publisher, signature, data)


def sigstore_checked(publisher: str, signature: str, data: bytes) -> bool | None:
    """The public channel's half: a Sigstore bundle, through `slipwai[verify]`, or `None` without it.

    Imported where it is used rather than at the top, because the whole point of the extra is that the keel
    runs without it — and an import at module scope would make every command that touches the trust store
    pay for a library most machines have not got. Any failure to *load* the verifier is `None`, the same as
    not having it; only a verification that ran and disagreed is `False`.
    """
    bundle = decoded(signature)
    if bundle is None:
        return False  # a signature that is not base64 at all is not a bundle anybody signed
    try:  # pragma: no cover - the extra is not installed in this repository's own gate
        from sigstore.models import Bundle  # noqa: PLC0415
        from sigstore.verify import Verifier  # noqa: PLC0415
        from sigstore.verify.policy import Identity  # noqa: PLC0415
    except ImportError:
        return None
    try:  # pragma: no cover - as above
        Verifier.production().verify_artifact(
            data, Bundle.from_json(bundle), Identity(identity=publisher, issuer=issuer_of(publisher)),
        )
    except Exception:  # noqa: BLE001 - every way a bundle fails to verify is the same answer here
        return False
    return True


def issuer_of(publisher: str) -> str:
    """The OIDC issuer a keyless identity was minted by. GitHub Actions is the only one `package release`
    signs from, so it is the only one a bundle is held to — an identity from somewhere else is somebody
    else's, whatever the string in front of it says."""
    return "https://token.actions.githubusercontent.com"


def state_of(publisher: str, signature: str, data: bytes | None = None, channel: str = "") -> str:
    """Which of the four states this release is in for this machine.

    An index that names no publisher is `unsigned`, not `untrusted`: there is nobody to have accepted, and a
    signature nobody claims proves nothing anyway. A `file:` channel on a person's own machine names none,
    and so does every index published before the field existed.

    `channel` is where the bytes came from, and it is in the refusal rather than only the publisher,
    because those are two different things to go and look at: a publisher whose key has moved on, and a
    channel serving a file that is not the one the publisher signed.
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
        where = f"the channel {channel} served" if channel else "the channel served"
        raise GenerationError(f"the signature {publisher} published for this release does not match the file "
                              f"{where}. Refusing to install it; tell {publisher} and "
                              f"{channel or 'the channel'}")
    return VERIFIED


def admitted(name: str, publisher: str, signature: str, data: bytes | None = None,
             confirm: bool = False, channel: str = "") -> str:
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
    return state_of(publisher, signature, data, channel)
