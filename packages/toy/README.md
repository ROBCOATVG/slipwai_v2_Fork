# slipwai-language-template

slipwai 2.0 language addon: slipwai-language-template.

This is `toy`, and **it is not a real language.** It is the smallest package slipwai's conformance suite accepts: the
family `toy` and its one backend `toy-plain` (framework `plain`), the `none` target, the in-memory and Postgres event
stores, every member of the backend protocol answered with a placeholder, and a one-line placeholder snippet for every
example marker a skill carries. A project generated with it builds nothing — its Makefile targets only `echo` what a
real language would run. It exists to be copied: rename it, then replace each placeholder with your language's own
answer while the suite stays green.

The backend carries a framework's name, not the family's bare `toy`, because slipwai's naming rule reserves a family's
name for what its backends share once it has two: named this way, a framework added beside it later is one new package
and renames nothing here (*Adding a framework*, below).

## What is here

| Path | What it is |
|---|---|
| `language.json` | The catalog fragment: the package's `name` (its directory's), the `core` schema range it loads on, `order`, `family`, and each backend's `label`, `targets` and per-axis `options` |
| `VERSION`, `CHANGELOG.md`, `changelog.d/` | The package's own version, independent of slipwai's, held to the same arithmetic (`changelog.d/README.md`) |
| `slipwai_language_toy/` | The Python: `__init__.py` exports `LANGUAGE`, the family (`family.py`) and the backend (`backend.py`) answering the protocol, and the pruning rows (`prune_rows.py`) |
| `assets/languages/toy/app/` | The files a service's directory starts with |
| `assets/languages/toy/flags/` | The feature-flag reader a service gets under a target that deploys |
| `assets/languages/toy/examples/<skill>/<id>.md` | One snippet per `{{example: <skill>/<id>}}` marker in slipwai's skills |
| `assets/backing-services/toy/` | What each `persistence` answer adds to a service, per rung (`write_side_files`, `read_side_files`) |
| `tests/test_conformance.py` | The conformance suite, as a `unittest` case over this package |

What every member means and the shape its answer takes is slipwai's backend-protocol contract, and how a package sits on
disk, what `language.json` holds and what is refused is its language-package contract. Both are in the slipwai
repository, under `specs/001-slipwai-2-language-addons/contracts/` (`backend-protocol.md`, `language-package.md`).

## Starting a language from it

1. Copy the repository into a directory of its own named for your language, `languages/mylang`: an installed
   package's directory name is its `name`, and the command line finds the package by it in the directory above.
2. Replace every `toy` and `Toy` the files hold with `mylang` and `Mylang`, and rename the four things named for it:
   the Python package `slipwai_language_toy/` (`slipwai_language_mylang/`; a dash in the name becomes `_`),
   `assets/languages/toy/`, `assets/backing-services/toy/` and the fragment `changelog.d/toy-language.md`. The rename
   is case-sensitive, so `s/toy/mylang/g` alone leaves two things behind: `language.json`'s `label`, which reads
   `Toy — the language template's inert placeholder…` and is what `slipwai list` and the interview show, and the
   fragment's file name. From a git clone this does all of it and leaves no `toy` or `Toy` in any file or path. It runs
   the same under GNU `sed` (Linux) and BSD `sed` (macOS): `-i.bak` is the in-place form both take, and the second line
   removes the backups it leaves. slipwai's own tests run this block, as written here, on a copy of this repository:

   ```sh
   git grep -lIi toy | xargs sed -i.bak 's/toy/mylang/g; s/Toy/Mylang/g'
   git ls-files --others '*.bak' | xargs rm -f
   git mv changelog.d/toy-language.md changelog.d/mylang-language.md
   git mv slipwai_language_toy slipwai_language_mylang
   git mv assets/languages/toy assets/languages/mylang
   git mv assets/backing-services/toy assets/backing-services/mylang
   ```

   That covers `language.json`'s `name`, `family`, `label` and backend key (`mylang-plain`: rename `plain` for your
   framework, or see *Adding a framework* for a language where nothing owns startup), the `Family` and `Backend` in
   `LANGUAGE` and the paths into `assets/`; `tests/test_conformance.py` reads the name from `language.json`. Then
   write the `label` as your language's own words. A name with a dash needs `_` in the Python package and its paths,
   which `sed` does not do for you.
3. Run the suite (below). It passes on the rename alone; from there, replace each placeholder with your language's
   answer, one at a time, and let the suite name what is still missing.
4. Say what your package ships in a fragment under `changelog.d/`. `VERSION` stays `1.0.0.dev0` until the first
   release, which you cut by hand (*Cutting a release*, below).

## Running the suite from this repository

The suite ships in slipwai itself as `slipwai.conformance`, so the only thing this repository needs is slipwai — **2.0
or newer**, the first with the suite. Hold it to that floor, so an older slipwai is a resolver error rather than a
missing module:

```sh
pip install --pre "slipwai>=2.0"                  # --pre while 2.0 is a snapshot: a .dev version is skipped without it
pip install ./slipwai-<version>-py3-none-any.whl  # or a wheel `make wheel` built from a slipwai checkout
uv run --prerelease allow --with "slipwai>=2.0" python -m slipwai.conformance .. toy   # the same, through uv
```

Then, from the package's directory (`languages/toy` here, `languages/mylang` once renamed), either:

```sh
python -m slipwai.conformance .. toy                              # one line per check, then passed or failed
python -m unittest discover -s tests -p test_conformance.py       # one test per check
```

The first is the command line: `python -m slipwai.conformance <language-dir> <package>`, where the language directory is
the one holding the package — here `languages`, the directory above, which should hold nothing else: every directory in
it is read as a package, and one that is not is refused in a line of its own. It prints `ok`, `FAILED` with each finding
under it, or `not run` and why, for each of `protocol`, `markers`, `profiles`, `targets`, `prune rows` and `version`,
and exits 0 when the package passed, 1 when it failed, 2 on a usage error and 3 when the suite itself could not run.

The second runs from any checkout, whatever its directory is called (a clone named `slipwai-language-template` too):
where the directory is not named for the package, the test copies the package under its name into a temporary language
directory first. It is `tests/test_conformance.py`, a subclass of `slipwai.conformance.ConformanceCase` that names its
`language_dir` (the directory this package sits in, `Path(__file__).resolve().parents[2]`) and its `package`. `unittest`
discovers it like any test module; each check is one test, failing with the same findings. Either way the checks run in
a fresh interpreter whose language directory is the one named, so whatever languages your own machine has installed are
never the ones checked.

## Trying it in a project

slipwai reads its languages from `~/.slipwai/languages`, or from the one directory `SLIPWAI_LANGUAGES` names instead.
Fill it from this checkout, which needs no network and no language index:

```sh
slipwai language install .          # copies this package to ~/.slipwai/languages/toy, under its name
slipwai list                        # toy, with its version
slipwai generate demo --backend toy-plain --frontend none --skip-checks --output /tmp/toy-demo
```

From a factory checkout, `slipwai list` reads empty of languages when neither `~/.slipwai/languages` nor
`SLIPWAI_LANGUAGES` names a directory that holds any: the checkout's own languages are under `languages/`, and the
command does not look there by itself. `SLIPWAI_LANGUAGES=languages ./slipwai list` lists them, and an empty list is
not a sign the toy is missing.

Install again after each change: the installed copy is a copy. Or point slipwai at the directory holding your clone for
one command, `SLIPWAI_LANGUAGES=.. slipwai list`, and nothing is copied; `SLIPWAI_LANGUAGES` replaces
`~/.slipwai/languages` whole, so only what that directory holds is loaded. The suite run above is against that same kind
of directory, so the copy in `~/.slipwai/languages` can be checked too: `python -m slipwai.conformance
~/.slipwai/languages toy`.

## Cutting a release

slipwai has no release command for a package: a release is cut by hand, and the suite's `version` check is what fails
whatever a hand-cut release gets wrong. Every number it names is the package's own, independent of slipwai's. From a
clean checkout of `main`, with the suite green:

1. **Assemble the entry.** Write every fragment in `changelog.d/` (all but its `README.md`) into `CHANGELOG.md` as the
   newest entry, above the ones there, under the heading `## <version> — <LEVEL>`: the release, and the highest level
   any fragment claims. The first release has no predecessor to bump, so its heading is `## 1.0.0` alone. Then delete
   the fragments; `changelog.d/README.md` stays.
2. **Write the release into `VERSION`**: the snapshot without its suffix, `1.0.0.dev0` becoming `1.0.0`.
3. **Run the suite.** `version` passes only where `VERSION` is the newest entry, that entry is there, and no fragment
   is left beside it.
4. **Commit and tag**: one commit, `Release <version>`, tagged `v<version>` exactly.
5. **Open the next snapshot** in the next commit: `VERSION` becomes the next PATCH as a snapshot (`1.0.1.dev0` after
   `1.0.0`), over a `changelog.d/` holding only its README. The first change that needs more raises it, beside its
   fragment.
6. **Push both at once**: `git push --atomic origin main v<version>`, so a released number never sits on `main`
   unpublished.
7. **Publish from the tag.** From a checkout of `v<version>`, `python3 scripts/language-index.py <index> <package>` in a
   slipwai checkout packs it and adds its entry. It refuses a package the `version` check fails and a number already
   spent: a release the index holds with other bytes, or a snapshot of a release it holds.

A released number is spent: never move a `v*` tag and never publish two packages under one number. The `version`
check refuses a release with no entry, one that is not the newest entry, one beside an unspent fragment, a snapshot of
a released number or below the newest entry, and a snapshot over an empty `changelog.d/` that claims more than the next
PATCH. The same steps are slipwai's language-package contract, *Cutting a package release*.

## Adding a framework

A framework of the family is a package of its own beside this one, and touches nothing here: its `language.json` names
`"family": "toy"`, `"requires": {"toy": ">=1.0,<2"}` (held against this package's `VERSION`) and one backend
`toy-<framework>` with its `framework`; its Python declares only that `Backend`, inherits every family-level answer, may
import this package's (`from slipwai_language_toy.backend import ANSWERS`), and reads the family's shared files through
`../toy/` the way `backend.py` does.

The smallest `__init__.py` such a framework needs, for `toy-web` in `slipwai_language_toy_web/`, hands the family's
answers to a new `Backend` under its own key:

```python
from slipwai import registry as protocol
from slipwai_language_toy.backend import ANSWERS

LANGUAGE = protocol.Language((), (protocol.Backend("toy-web", "toy", dict(ANSWERS)),))
```

Beside a copy of this package named `toy`, with a `language.json` and `VERSION` of its own, that passes the suite
(`python -m slipwai.conformance .. toy-web`). Reusing `ANSWERS` whole is enough while the framework writes the same files
as `toy-plain`: its store sources start with `../toy/`, so they resolve to the family's copy from any sibling directory.

Re-key `SERVICE_FILES` once the framework answers anything of its own. The inherited `service_files` passes the key
`toy-plain` to `backing_service_service_files` and `flag_reader`, which read that backend's layout, store sources and
flag reader, so a framework with a store source, a skeleton or a flag reader of its own is not read until its
`service_files` passes its own key. The store sources (`WRITE_SIDE_FILES`, `READ_SIDE_FILES`) are re-keyed when the
framework replaces them or when they are bare names relative to the family's directory: each source then gains the
`../toy/` prefix, so it reaches the family's copy from the framework's directory. The suite passes a framework that
reuses `ANSWERS` whether or not it needed either, so this is a decision to make, not one to wait for a failure on.
slipwai's own tests write a framework that re-keys both beside a copy of this template and run the suite over both
(`write_scratch_framework` in `tests/test_language_template.py` in the factory's repository).

## The import surface

A package's Python may import only the slipwai modules listed under *The core modules a package imports* in
`contracts/language-package.md`, and nothing else of core. That list is the part of slipwai a package is built against;
a package that imports beyond it can break on any slipwai release. Your `tests/` are outside the rule.

The check that holds it is slipwai's own `make check-structure`, which reads the list from that page and refuses, by
file, line and module, any import outside it under `languages/*/slipwai_language_*/`. It runs in a slipwai checkout, not
from this repository: put a copy of the package there and run it.

```sh
git clone https://github.com/luke-gee/slipwai-cruise-2 slipwai && cd slipwai   # the factory's repository, for now
git submodule update --init                          # the first-party packages the check reads beside yours
cp -r ../mylang languages/mylang                     # outside the copy, nothing of slipwai changes
python3 scripts/check-structure.py                   # what `make check-structure` runs
rm -rf languages/mylang
```

The template's own Python imports only `slipwai.registry`, `slipwai.assets`, `slipwai.backends`, `slipwai.selection`,
`slipwai.services`, `slipwai.tooling`, `slipwai.project.backing_services`, `slipwai.project.flags` and
`slipwai.project.renovate`, all on the list.
