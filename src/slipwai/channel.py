"""A channel as a repository: what it holds, what is checked before an entry joins it, and what it serves.

A channel is a directory of JSON and release files served as static files. That is the whole of it, and it
is deliberate: a private channel and the public one are then the same thing, so an organisation's channel is
tested by the same code and contributed to the same way as the one everybody uses.

**One file per release, and the index is built from them.** `entries/<name>-<version>.json` is what a
publisher adds; `slipwai-languages/index.json` is a regeneration of all of them. Two publishers releasing on
one afternoon touch two files and never meet, and nobody resolves a conflict in a document a client reads.

**What the check is for is the pull request.** The public channel takes contributions from people the
channel's owners have never met, so the questions it asks are the ones a reviewer cannot answer by reading:
is the file the entry names actually there, is its digest the digest claimed, does the manifest load, and is
this name already somebody else's. A reviewer reads the description and the code; the machine reads the
rest.

**A name belongs to its first publisher.** The one check that is a policy rather than a fact. Somebody who
published `python` keeps `python`, and a second publisher using that name is refused by name — because the
alternative is that an install silently starts fetching a different person's code under a name a project
already depends on.
"""
from __future__ import annotations

import hashlib
import json
import urllib.parse
from pathlib import Path

from .index_schema import KINDS, entry_of, format_of
from .package_release import DOCUMENT, ENTRIES, document, entries_in

SERVING = DOCUMENT.rsplit("/", 1)[0]


def release_file(channel: Path, entry: dict) -> Path:
    return channel / SERVING / str(entry.get("file", ""))


def claims(entries: list[dict]) -> dict[str, set[str]]:
    """Each name, and every publisher that has listed a release under it."""
    found: dict[str, set[str]] = {}
    for entry in entries:
        found.setdefault(str(entry["name"]), set()).add(str(entry.get("publisher", "")))
    return found


def elsewhere(entry: dict) -> str:
    """The absolute URL this entry's file is at, or `''` where the file is beside the index.

    A publisher hosting their own bytes is the ordinary arrangement and the one that scales: a channel
    that stored every tarball would grow a copy of every version for ever, and a contributor's pull
    request would carry a binary a reviewer cannot read.
    """
    found = str(entry.get("file") or "")
    # `file:` counts, because a channel tried as a `file:` tree is how a private one is tried before it is
    # published and how this is tested. Listing one in a public channel is not a way in: the client
    # refuses a `file:` release named by an index that is not itself a `file:` tree.
    return found if urllib.parse.urlsplit(found).scheme in ("http", "https", "file") else ""


def fetched_findings(entry: dict, url: str) -> list[str]:
    """Fetch a file the publisher hosts and hold it to the digest the entry publishes.

    This is what makes somebody else's URL safe to list. The publisher can replace the asset after the
    pull request merges — nobody can stop them — and the digest is why that costs them their own package
    rather than anybody's trust: the client refuses bytes that are not the bytes the index named.
    """
    from .language_index import RELEASE_LIMIT, Unreachable, fetch
    name, version = entry["name"], entry.get("version")
    try:
        data = fetch(url, "the channel", url, RELEASE_LIMIT)
    except Unreachable as fault:
        return [f"{name} {version}: {url} could not be fetched ({fault.reason}). A file the index names "
                f"and nobody can reach is an entry that installs for nobody"]
    if hashlib.sha256(data).hexdigest() != entry.get("sha256"):
        return [f"{name} {version}: {url} is not the file the entry publishes a digest of. Either the "
                f"entry or the file was changed after the other; release a new version"]
    return []


def file_findings(channel: Path, entry: dict, fetch_remote: bool = False) -> list[str]:
    """What is wrong with one entry's release file: missing, or not the bytes the entry's digest names."""
    name, version = entry["name"], entry.get("version")
    if not entry.get("file"):
        return [f"{name} {version}: the entry names no file"]
    url = elsewhere(entry)
    if url:
        return fetched_findings(entry, url) if fetch_remote else []
    path = release_file(channel, entry)
    if not path.is_file():
        return [f"{name} {version}: {path.relative_to(channel)} is not in this channel, and the entry "
                f"names no URL it is at instead"]
    held = hashlib.sha256(path.read_bytes()).hexdigest()
    if held != entry.get("sha256"):
        return [f"{name} {version}: {path.relative_to(channel)} is not the file the entry publishes a digest "
                f"of. Either the entry or the file was changed after the other; release a new version"]
    return []


def shape_findings(entry: dict) -> list[str]:
    """Whether the client would read this entry at all, asked by the client's own reader.

    Asked here rather than described: an entry the client drops is an entry nobody can install and nothing
    says why, which in a public channel is a contributor who followed the instructions and got silence.
    """
    name = str(entry["name"])
    body = {key: value for key, value in entry.items() if key != "name"}
    if entry.get("kind") not in KINDS and not any(isinstance(entry.get(kind), dict) for kind in KINDS):
        return [f"{name}: the entry declares no kind and carries no manifest, so nothing can be read from it"]
    if entry_of("https://example.invalid/index.json", name, body) is None:
        return [f"{name} {entry.get('version')}: the client would drop this entry. Check its version, its "
                f"sha256, and that its manifest is the one the keel reads for its kind"]
    return []


def check(channel: Path, fetch_remote: bool = False) -> list[str]:
    """Everything wrong with this channel, a line each. Empty is a channel that serves what it claims to.

    `fetch_remote` fetches each file a publisher hosts elsewhere and holds it to its digest. Off by
    default, so a person checking a channel on a train is not waiting on a hundred downloads; on in CI,
    which is where a pull request from somebody nobody knows is actually decided.
    """
    try:
        entries = entries_in(channel)
    except Exception as error:  # a channel whose entries cannot be read is one finding, not a traceback
        return [str(error)]
    findings: list[str] = []
    for entry in entries:
        findings += shape_findings(entry)
        findings += file_findings(channel, entry, fetch_remote)
    for name, publishers in sorted(claims(entries).items()):
        named = sorted(one for one in publishers if one)
        if len(named) > 1:
            findings.append(f"{name} is listed by {' and '.join(named)}. A name belongs to its first "
                            f"publisher: a second one under the same name would have an install silently "
                            f"start fetching different code under a name a project already depends on")
    findings += index_findings(channel, entries)
    return findings


def index_findings(channel: Path, entries: list[dict]) -> list[str]:
    """Whether the served index is what the entries render to. A regeneration, checked rather than trusted."""
    path = channel / DOCUMENT
    if not path.is_file():
        return [f"{DOCUMENT} is not in this channel; `slipwai channel build {channel}` writes it"]
    try:
        served = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as error:
        return [f"{DOCUMENT} cannot be read: {error}"]
    if format_of(served) is None:
        return [f"{DOCUMENT} is not an index document this keel reads"]
    if served != document(entries):
        return [f"{DOCUMENT} is not what {ENTRIES}/ renders to. It is generated, never edited: "
                f"`slipwai channel build {channel}` rewrites it"]
    return []
