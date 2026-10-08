"""`slipwai channel new`: a channel repository, ready to serve and ready to take a contribution.

The same files whichever kind of channel it is. A private one is this directory on an internal host; the
public one is this directory under `ROBCOATVG`, served by Pages. Making them the same shape is what keeps
the public channel honest: it is tested by the code every private channel runs, not by itself.
"""
from __future__ import annotations

import json
from pathlib import Path

from .errors import GenerationError
from .package_release import DOCUMENT, ENTRIES, SETTINGS

SERVING = DOCUMENT.rsplit("/", 1)[0]





def files(name: str, base: str = "") -> dict[str, str]:
    """Every file a channel repository starts with."""
    return {
        # What the front page calls this channel and where it is served from. Written once so `build`
        # need not be told them again, and read by nothing else — the client is told the base by
        # `SLIPWAI_CHANDLERY` and never by the channel.
        SETTINGS: json.dumps({"name": name, "base": base}, indent=2, ensure_ascii=False) + "\n",
        f"{ENTRIES}/README.md": ENTRIES_README,
        "README.md": README.format(name=name),
        "CONTRIBUTING.md": CONTRIBUTING.format(name=name),
        ".github/workflows/channel.yml": WORKFLOW,
        ".gitignore": "__pycache__/\n",
    }


#: What a directory may already hold and still count as empty. A fresh clone of the repository somebody
#: made for this is the normal place to run `channel new`, and it has a `.git` in it — refusing that sent
#: people to an empty directory they then had to turn into a repository by hand.
ALLOWED = {".git", ".gitignore", ".DS_Store", "README.md", "LICENSE"}


def occupied(into: Path) -> list[str]:
    """What is in the way, or nothing. Named rather than counted, so a refusal says what to move."""
    if not into.exists():
        return []
    return sorted(one.name for one in into.iterdir() if one.name not in ALLOWED)


def write(name: str, into: Path, base: str = "") -> list[str]:
    """Write the channel under `into`, or refuse a directory that already holds something of its own."""
    if (found := occupied(into)):
        raise GenerationError(f"{into} already holds {', '.join(found[:5])}. A channel is a whole "
                              f"repository, so it is written into an empty directory or a fresh clone")
    for path, text in files(name, base).items():
        target = into / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    (into / SERVING).mkdir(parents=True, exist_ok=True)
    return [str(into / path) for path in files(name)]


ENTRIES_README = """# entries

One file per release: `<name>-<version>.json`, written by `slipwai package register`.

Never edit one by hand and never edit `../slipwai-languages/index.json` — it is generated from this
directory by `slipwai channel build`, and CI refuses a pull request where the two disagree.

One file per release is the point: two publishers releasing on the same afternoon touch two files and never
meet, so nobody resolves a merge conflict in a document that clients read.
"""

README = """# {name}

A slipwai chandlery channel: the languages and extensions this channel serves, and the release files
themselves.

## Installing from it

```sh
export SLIPWAI_CHANDLERY=<this channel's base URL>
slipwai search
slipwai install <a language>
slipwai extension install <an extension>
```

Several channels are named in order, comma-separated — an organisation's own first, this one after it. A
name an earlier channel lists is that channel's.

## What is in here

| Path | What it is |
| --- | --- |
| `entries/<name>-<version>.json` | One file per release. The only thing a contribution adds |
| `slipwai-languages/index.json` | Generated from `entries/`. Never edited |

A release file lives on the tag that built it, not here: git keeps every version of every file for ever,
and a channel holding its own tarballs grows without bound. An entry names the URL and the digest, and the
digest is what makes somebody else's URL safe to list — a publisher who replaces the file afterwards has
broken their own package, because the client refuses bytes that are not the bytes the index named.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). It is four commands.

## Which keel checks this

CI installs `slipwai` from PyPI and runs `slipwai channel check .` — the keel's own code, not this
repository's, because a channel that checks itself is only as good as that channel.

To check against a keel that is not on PyPI yet, set a repository variable:

```sh
gh variable set SLIPWAI_KEEL -R <owner>/<repo> --body 'git+https://github.com/ROBCOATVG/slipwai@main'
```

Unset it once the version you need is published.
"""

CONTRIBUTING = """# Publishing to {name}

Four commands. Everything else is read off your package.

```sh
slipwai package new <name>          # a package that already loads, with TODOs where decisions go
slipwai package check .             # the conformance suite your package's kind is held to
slipwai package register . --channel <a checkout of this repository> --publisher <you>
                                    # builds the release file, writes its entry, rebuilds the index
git switch -c publish-<name>-<version> && git add -A && git commit && git push
```

Then open a pull request. CI runs `slipwai channel check`, which asks the questions a reviewer cannot
answer by reading:

- the release file the entry names is fetched and its sha256 is the one the entry publishes;
- the entry is one the client would actually read, manifest and all;
- the index is what `entries/` renders to, because it is generated and never edited;
- the name is not already another publisher's.

**A name belongs to its first publisher.** Somebody who published `python` keeps `python`. The alternative
is an install silently fetching a different person's code under a name a project already depends on.

**A release is immutable.** Changing the file under a version somebody has installed makes a digest they
checked into a lie. Release a new version instead; `register` refuses the other thing — and if you replace
the asset your tag hosts, every install of that version starts failing, which is a thing you have done to
yourself rather than to anybody who trusted you.

Your package's own CI should call the keel's reusable workflow, which `slipwai package new` writes for you.
"""

WORKFLOW = """name: channel

# What a pull request to this channel is checked against: the keel's own `slipwai channel check`, which is
# the same code a private channel runs. The channel is not checked by itself — that is the whole reason the
# check lives in the keel.

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: '3.11'
      # Which keel checks this channel. `slipwai` from PyPI is the answer once version 2 is published
      # there; until then it is not, and a channel created today would install a keel with no `channel`
      # verb in it and fail on the first push with a usage error. So it is a repository variable:
      #
      #   gh variable set SLIPWAI_KEEL -R <owner>/<repo> \
      #     --body 'git+https://github.com/ROBCOATVG/slipwai@main'
      #
      # Unset, it installs `slipwai`, which is what every channel should end up doing.
      - name: Install the keel that checks this channel
        run: |
          set -eu
          python -m pip install --disable-pip-version-check "${{ vars.SLIPWAI_KEEL || 'slipwai' }}"
          slipwai --version
      # `--fetch` because this is where a pull request from somebody nobody knows is decided: every file
      # a publisher hosts themselves is downloaded and held to the digest their entry publishes. Without
      # it the check is a read of the JSON, which proves the entry is well formed and nothing about the
      # bytes it names.
      - name: Check the channel
        run: slipwai channel check . --fetch

  publish:
    needs: check
    if: github.ref == 'refs/heads/main' && github.event_name != 'pull_request'
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v6
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: .
      - id: deployment
        uses: actions/deploy-pages@v4
"""
