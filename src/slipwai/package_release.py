"""Building a release of either kind of package, and putting it in a channel.

A release is three things: a file, a digest of that file, and an entry in a channel's index saying where the
file is and what is in it. Version 1 had the first two and a person wrote the third by hand, into one
`index.json` that every publisher edited — which is the shared line every other part of this method has
already removed once, and it goes the same way here.

**One file per entry.** A channel repository holds `entries/<name>-<version>.json`, and its index is built
from them. Two publishers releasing on one afternoon touch two files and never meet; the index is a
regeneration rather than a resolution, which is `changelog.d/`'s shape and `render-fairways`' and the
events index's.

**The entry is written from the package, never typed.** Its manifest, its version, its digest: all of it is
read off the thing being released. What a publisher writes is the description and the tags, in the manifest,
where they are also what the keel reads — so there is one place to get them wrong rather than two places to
get them out of step.

**Registering is a file operation, and that is deliberate.** A channel is a directory of JSON and release
files, served as a static site. `register` writes into a checkout of one; whether that checkout is pushed,
reviewed or merged is the channel's own business, which is what makes a private channel and the public one
the same shape (6.6 is the public one's review path).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .errors import GenerationError
from .index_schema import BLOCK, EXTENSION, LANGUAGE
from .language_release import ReleaseError, pack, read_package

#: Where a channel keeps one file per release, and the document built from them.
ENTRIES = "entries"
DOCUMENT = "slipwai-languages/index.json"
FORMAT = 2
#: What an entry declares about itself beyond the manifest. Read off the package or given by the publisher;
#: none of it is typed twice.
CARRIED = ("publisher", "description", "tags")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def kind_of(root: Path) -> str:
    """Which kind of package this directory is, by the manifest it holds."""
    if (root / "extension.json").is_file():
        return EXTENSION
    if (root / "language.json").is_file():
        return LANGUAGE
    raise GenerationError(f"{root} holds neither a language.json nor an extension.json, so it is no package")


def entry_for(root: Path, archive: Path, publisher: str = "") -> dict:
    """The index entry for a built release: where the file is, what is in it, and who says so.

    The file is named relative to nothing — a channel's index and its release files sit in one directory, and
    the client joins the name against the document's own URL. A channel that serves them from elsewhere
    rewrites this one field, which is the only field that is about where rather than about what.
    """
    source = read_package(root)
    if source.version == "unknown":
        raise GenerationError(f"{root} has no VERSION, and a release is a version of something. Write one: "
                              f"`echo 0.1.0 > {root / 'VERSION'}`")
    kind = kind_of(root)
    manifest = source.fragment
    entry = {
        "version": source.version,
        "file": archive.name,
        "sha256": digest(archive),
        "kind": kind,
        kind: manifest,
    }
    if publisher:
        entry["publisher"] = publisher
    for field in ("description", "tags"):
        if manifest.get(field):
            entry[field] = manifest[field]
    return entry


def written_entry(name: str, entry: dict, into: Path) -> Path:
    """One entry file, `<name>-<version>.json`, which is the only file a release adds to a channel's listing."""
    into.mkdir(parents=True, exist_ok=True)
    path = into / f"{name}-{entry['version']}.json"
    path.write_text(json.dumps({"name": name, **entry}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def release(root: Path, out: Path, publisher: str = "") -> tuple[Path, Path, dict]:
    """Build the release file and its entry under `out`. (file, entry file, entry). Writes nowhere else."""
    try:
        archive = pack(root, out)
    except ReleaseError as error:
        raise GenerationError(str(error)) from None
    entry = entry_for(root, archive, publisher)
    return archive, written_entry(read_package(root).name, entry, out / ENTRIES), entry


def entries_in(channel: Path) -> list[dict]:
    """Every entry file a channel holds, in name then file order, each with the name it is listed under."""
    place = channel / ENTRIES
    found: list[dict] = []
    for path in sorted(place.glob("*.json")) if place.is_dir() else []:
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError) as error:
            raise GenerationError(f"{path} cannot be read as an entry: {error}") from None
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise GenerationError(f"{path} names no package, so nothing can be listed under it")
        found.append(entry)
    return found


def document(entries: list[dict]) -> dict:
    """The index document those entries render to. Deterministic, because it is checked rather than trusted."""
    packages: dict[str, list[dict]] = {}
    for entry in entries:
        body = {key: value for key, value in entry.items() if key != "name"}
        packages.setdefault(entry["name"], []).append(body)
    for listed in packages.values():
        listed.sort(key=lambda body: str(body.get("version")))
    return {"index": FORMAT, BLOCK[FORMAT]: dict(sorted(packages.items()))}


def rebuild(channel: Path) -> Path:
    """Write the channel's index from its entry files, and return where it went."""
    path = channel / DOCUMENT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document(entries_in(channel)), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def register(root: Path, channel: Path, publisher: str = "") -> tuple[Path, Path, Path]:
    """Build a release of `root` into `channel` and rebuild its index. (file, entry file, index).

    Refuses a version the channel already lists with different bytes. A release file is immutable by the
    time anyone has installed it, and replacing one silently is how a digest somebody checked stops meaning
    anything. Re-registering the same bytes is allowed and does nothing new, so a publisher who ran this
    twice has not got a problem to solve.
    """
    name = read_package(root).name
    serving = channel / DOCUMENT.rsplit("/", 1)[0]
    try:
        archive = pack(root, serving)
    except ReleaseError as error:
        raise GenerationError(str(error)) from None
    entry = entry_for(root, archive, publisher)
    standing = channel / ENTRIES / f"{name}-{entry['version']}.json"
    if standing.is_file():
        held = json.loads(standing.read_text(encoding="utf-8"))
        if held.get("sha256") != entry["sha256"]:
            raise GenerationError(f"{channel} already lists {name} {entry['version']}, with a different file. "
                                  f"A release is immutable once anybody has installed it: release a new "
                                  f"version rather than replacing this one")
    return archive, written_entry(name, entry, channel / ENTRIES), rebuild(channel)
