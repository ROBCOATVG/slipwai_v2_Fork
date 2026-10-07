# Contract — an extension package

An **extension** is optional dev tooling a project elects at `./init`. It never changes generated code, so
it is not a product-architecture choice and has no answer in `slipwai generate`; it is installed into the
package directory beside the languages, offered by `./init`'s menu in every project generated after that,
and elected there or later with `./init --extension <key>`.

This page is the whole contract: what the manifest declares, what the entry point has to do, where the files
land, and what the keel refuses. `src/slipwai/extension_shape.py` holds the manifest half and
`tests/test_extension_package.py` holds the loader and installer half, so this page and the code move
together or the gate is red.

## Where it lives

| Thing | Module | Tier (`scripts/check-structure.py`) |
|---|---|---|
| What a manifest declares, and the six obligations | `src/slipwai/extension_shape.py` | contract |
| Reading a package off disk | `src/slipwai/extension_directory.py` | contract |
| Folding one into the catalogue | `src/slipwai/extensions.py` | contract |
| The points a hook may attach to | `src/slipwai/hooks.py` | contract |
| Installing and removing one | `src/slipwai/extension_install.py` | edge |
| Writing a new one | `src/slipwai/package_new.py`, `slipwai package new` | edge |
| Firing a point inside a project | `assets/toolkit/scripts/extensions/hooks.py` | the toolkit's, not the keel's |

The last row is the rule that has been learned twice: **anything a generated project runs is a toolkit
script**, because a generated project has no slipwai to import. The keel decides what an extension *is*; the
toolkit runs it.

## The manifest

`extension.json`, at the root of the package directory.

| Field | Required | What it is |
|---|---|---|
| `key` | yes | What a person types — `./init --extension <key>` — and what the installed directory is called. A lower-case slug. |
| `name` | yes | What `./init`'s menu shows. A product's own name, so "UI/UX Pro Max" is fine here and nowhere else. |
| `description` | yes | One sentence the menu shows under the name. For most people this is the only thing they will ever read about it. |
| `kind` | yes | `extension`. The loader reads this and `language.json` apart by the file's name; the field is how a manifest in the wrong file is refused with the right advice. |
| `core` | yes | The keel schema range it is built for, e.g. `>=9.0,<10`. Outside it, the refusal names the command that moves whichever of the two is behind. |
| `ignore` | no | gitignore text for whatever local state it leaves. |
| `publisher` | no | Who published it, which the chandlery's index shows. |
| `tags` | no | What `slipwai search` matches against. |
| `hooks` | no | The points it attaches to — below. |

`key` and `name` are separate because they are different things, and this is the one way an extension's
manifest differs from a language's, where the name is both. The catalogue entry a project gets carries
`name`, `description` and `ignore`; the rest is the keel's business.

## The six obligations

Each is a failure somebody had. `slipwai extension check <dir>` prints them;
`python -m slipwai.conformance --extension <dir>` runs them, against a scratch project it builds and throws
away. Four are run — `idempotent`, `non-fatal`, `projects` and `merges` are facts about what the entry point
did, so it is run twice and then once more with nothing on `PATH`. `gated` is a fact about what the package
ships. `recovers` is checked against what the entry point actually printed: a line reporting a problem that
names no command is the failure the obligation exists to stop. A check the suite could not reach says `not
run` with the reason rather than passing quietly.

1. **Idempotent** — running `./init --extension <key>` twice does what running it once did. Anything else
   turns "did it work?" into "how many times has it run?".
2. **Non-fatal** — a dev tool that is not on this machine is not a reason a project cannot be set up. It
   says what is missing, and the project still works.
3. **Projects** — its `AGENTS.md` block sits between markers, so the next projection replaces exactly that
   block and leaves what a person wrote around it.
4. **Gated** — an extension that writes an index, a cache or a lock ships a `check-<key>.py`, because stale
   state nothing checks is state nobody trusts and everybody rebuilds.
5. **Recovers** — every failure path names the command that fixes it. A message saying what is wrong and
   not what to do about it costs its reader a search.
6. **Merges** — a file a person hand-edited is merged, never overwritten. Anything else means an edit lost
   to an install run for an unrelated reason, which is how a tool becomes one people avoid running.

## The hook points

A hook attaches to a point; it does not invent one. The set is closed, like the axes: a point is a promise
the keel keeps about when something runs and what it is given, and a point an extension could add would be a
promise nobody made. `slipwai hooks` prints the set with what is attached to each.

| Point | Fires | Given |
|---|---|---|
| `init` | `./init --extension <key>`, once per election | `root` |
| `project` | every re-projection: `make agents`, `migrate`, `./init --integration` | `root`, `harnesses` |
| `check` | `make check-extensions`, as one more gate | `root` |
| `before-stage` | before each rung of the ladder | `stage`, `slice`, `fairway`, `berth` |
| `after-stage` | after each rung of the ladder | `stage`, `slice`, `fairway`, `berth` |
| `boundary` | every captain boundary, after the inbox is read | `slice`, `fairway`, `lines` |
| `before-merge` | on the rebased branch, before the full gate | `slice`, `fairway`, `diff` |

Declared short — `"hooks": {"init": "init.py"}` — or long, with `run`, `stages` and `budget`:

```json
{
  "hooks": {
    "after-stage": {"run": "hooks/sync.py", "stages": ["implement", "converge"], "budget": "30s"}
  }
}
```

What is given arrives in the environment as `SLIPWAI_STAGE`, `SLIPWAI_SLICE` and so on.

Three rules keep a hook from becoming a second control plane:

- **The captain depends on no hook.** Its controls — the last line, the controlled-files diff, the bounded
  waits, the inbox receipt — all work with every hook removed. A hook is a second belt.
- **A hook is never fatal to the rung.** It is reported as a `hook` line naming the extension, the point and
  the last thing it printed, and the rung completes. An extension that could fail a stage is an extension
  that can stop a delivery loop it was added to help. The `check` point is the one exception, and
  `make check-extensions` is its only caller: that point *is* a gate, and a gate that cannot fail is not one.
- **The resolved registry is a controlled file.** `.slipwai/hooks.json` is written from the elected
  extensions, and an iteration that edits it is refused like one that edits a gate — so a run cannot
  register a hook on itself.

## Where the files land

Every file of the package but `extension.json` is written into a generated project at
`scripts/extensions/<key>/`, with `scripts/extensions/available.json` beside them carrying each offered
extension's hooks. The manifest is not copied: a project is not where one is read, and shipping it there
would ship a decoy that nothing reads and everybody edits.

The project gets the files at **generation**, not at election, because the menu `./init` shows is built from
the catalogue and the election happens inside the project, where there is no keel to fetch anything. What is
offered is therefore exactly what `./init` can run. An extension installed after a project was generated
reaches it at the next `slipwai migrate`.

## Writing one

```sh
slipwai package new <key>                  # a whole package that already loads
slipwai package check <dir>                # the conformance suite for whichever kind it is
slipwai package release <dir>              # the release file, its digest and its index entry
slipwai package register <dir> --channel <checkout>   # both of those, into a channel
slipwai extension check <dir>              # just the manifest, and the six it is held to
slipwai extension install <key>            # into the package directory
slipwai extension list                     # what is installed, and what each attaches to
slipwai hooks                              # every point, and what is on it
```

The scaffold ships a `Makefile` with `check`, `release` and `register` and a CI workflow that calls the
keel's reusable one, so the four verbs are `make check` and `make register CHANNEL=...` from inside the
package.

A channel is a directory: `entries/<name>-<version>.json`, one file per release, and
`slipwai-languages/index.json` built from them. Two publishers releasing on one afternoon touch two files
and never meet, and the index is a regeneration rather than a resolution — `changelog.d`'s shape again. A
version already listed with different bytes is refused: a release is immutable once anybody has installed
it, and replacing one silently is how a digest somebody checked stops meaning anything.

`package new` writes a manifest declaring the schema *this* keel speaks, and an entry point that already
meets obligations 1, 3 and 6 with the rest marked `TODO`. A scaffold that does not load is a scaffold whose
first lesson is that the tool is broken.

An install takes a name, a package directory, a release file or a git URL. A name with no separator in it is
looked up in the chandlery; anything with one is a path, so a mistyped path is a refusal and never a silent
network call. A clone is shallow and its `.git` is dropped on the way in: what is installed is the package,
not its history.

## Channels

`SLIPWAI_CHANDLERY` names the channels to ask, comma-separated, in order — an organisation's own first and
the public one after it. The order is the whole of the policy: **a name an earlier channel lists is that
channel's**, versions and all, so an organisation can publish its own `python` and have it win without
anything else being configured. Merging the version lists instead would make one install fetch from whichever
channel happened to publish most recently.

`SLIPWAI_INDEX` is still read and is asked last. It is the keel's own upgrade index as well as a package
channel, so a person who set it to a mirror meant "fetch from here", not "and never ask anywhere else".

One channel being unreachable is said and the rest are still listed. Every channel being unreachable is a
refusal, because "nothing available" and "could not ask" are different answers and a person acts on them
differently.

## What is refused, and where

A manifest is right or wrong on its publisher's machine, so everything about its shape is refused by
`extension check` before anything is published. Two things can only be known on the machine installing it,
and are refused there: a `key` some other package already holds, and a package whose `core` range this keel
does not satisfy. A refused extension is refused alone — it is optional dev tooling, and a project that
cannot be generated because something optional is malformed has the dependency backwards.

## Who you install from

Installing a package is running somebody else's code: a language's Python is imported into the keel, and an
extension's entry point edits the project. The digest the index publishes proves the file is the file the
index listed; it says nothing about who listed it.

So a package whose index names a publisher is asked about **once**. Accept them and every later release
installs silently; `slipwai trust list` shows who is accepted, `slipwai trust add <publisher>` does it
beforehand (a container image, a CI runner), and `slipwai trust remove` undoes it. `ROBCOATVG` is seeded as
a row like any other, which can be removed — that is the difference between a default and a rule.

A release is in one of four states, and `slipwai show` says which:

| State | What it means |
|---|---|
| `verified` | a signature was checked and matched |
| `unverified` | a signature is carried, and this copy has no verifier for it |
| `unsigned` | the index carries no signature, or names no publisher to attribute one to |
| `untrusted` | the publisher is not one this machine has accepted |

`unverified` is kept apart from `verified` deliberately. The one thing a signature must never be used to say
is "signed" about a signature nobody looked at. Which verifier fills `verified` is an open decision recorded
in the plan: Python's standard library has no X.509 and no ECDSA, so a Sigstore bundle cannot be checked by
a keel that ships with no dependencies.

## The keel ships none

Version 1 carried three extensions in its own `catalog.json`. They are packages now —
`ROBCOATVG/slipwai-extension-codegraph`, `-uipro`, `-ux-gates`. An extension that lived in the keel would be
a dev tool every project carries the description of, whether or not anyone wanted it.
