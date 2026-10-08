"""`slipwai package new`: a language or an extension package that loads on the first try.

Both kinds of package are a directory, a manifest and some files, and both have a shape the loader refuses
for reasons a publisher cannot guess from the outside — a `core` range, a module name derived from the
package's own, a `LANGUAGE` the fragment has to agree with, an entry point meeting six obligations. Version 1
had no scaffold for either, and every package anyone wrote started as a copy of one that already worked,
carrying whatever was wrong with it.

**So the keel writes the skeleton, and the skeleton is one the keel loads.** What `package new` emits passes
`extension check` or installs as a language the moment it is written, with the parts a publisher has to fill
marked `TODO` rather than left out. A scaffold that does not load is a scaffold whose first lesson is that
the tool is broken.

**The manifest is written from this keel's schema, not from a constant.** A package scaffolded today declares
the range this copy speaks, so it is current by construction and nobody has to know what to put there.
"""
from __future__ import annotations

import json
from pathlib import Path

from .assets import this_command
from .errors import GenerationError
from .extension_shape import OBLIGATIONS
from .language_shape import name_fault

#: Where the reusable workflow a package's CI calls actually lives. Version 1's repository has a
#: `package.yml` too, with different inputs — a package pointed at it would fail on the first push with
#: inputs that workflow has never heard of. This becomes `ROBCOATVG/slipwai` when version 2 merges back
#: there (slice 8.5), and that row says so.
KEEL_REPO = "ROBCOATVG/slipwai_v2_Fork"
KINDS = ("extension", "language")
#: The publisher's verbs, in the order they are used.
VERBS = ("new", "check", "release", "register")
#: What a scaffolded manifest declares it needs: this keel's schema, and everything up to the next major.
def core_range(schema: str) -> str:
    major = schema.split(".")[0]
    return f">={schema},<{int(major) + 1}"


def title_of(name: str) -> str:
    """A key as a human name: `ux-gates` becomes `Ux gates`, which the publisher then edits."""
    return name.replace("-", " ").capitalize()


def module_of(name: str) -> str:
    return f"slipwai_language_{name.replace('-', '_')}"


def checked(kind: str, name: str) -> str:
    """The name, or the refusal that says what a package may be called."""
    if kind not in KINDS:
        raise GenerationError(f"a package is a {' or a '.join(KINDS)}; `--kind {kind}` is neither")
    fault = name_fault(kind, name)
    if fault is not None:
        raise GenerationError(f"{fault}. It becomes a directory, a key and part of a command, so it is held "
                              f"to what all three allow")
    return name


def extension_files(name: str, schema: str) -> dict[str, str]:
    """An extension package: its manifest, an entry point that already meets the six, and a README saying so."""
    manifest = {
        "key": name,
        "name": title_of(name),
        "description": f"TODO: one sentence `./init`'s menu shows for {name}. What it installs, and what it "
                       f"is for — the menu is the only place most people read about it.",
        "kind": "extension",
        "core": core_range(schema),
        "hooks": {"init": "init.py"},
    }
    obligations = "\n".join(f"{index}. **{said[0].upper()}{said[1:]}** — `{key}`."
                            for index, (key, said) in enumerate(OBLIGATIONS, start=1))
    return {
        "extension.json": json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        "VERSION": "0.1.0\n",
        "init.py": ENTRY_POINT.format(name=name, title=title_of(name)),
        "README.md": README.format(name=name, title=title_of(name), obligations=obligations,
                                   command=this_command()),
        "Makefile": MAKEFILE.format(name=name, kind="extension"),
        ".github/workflows/verify.yml": WORKFLOW.format(name=name, kind="extension", keel=KEEL_REPO),
    }


def language_files(name: str, schema: str) -> dict[str, str]:
    """A language package: its fragment, its `VERSION`, and the Python module the loader imports."""
    fragment = {
        "name": name,
        "core": core_range(schema),
        "order": 100,
        "family": name,
        "backends": {name: {"label": f"{title_of(name)} — TODO: the framework, in a few words",
                            "family": name}},
    }
    module = module_of(name)
    return {
        "language.json": json.dumps(fragment, indent=2, ensure_ascii=False) + "\n",
        "VERSION": "0.1.0\n",
        f"{module}/__init__.py": LANGUAGE_MODULE.format(name=name, module=module, title=title_of(name)),
        "README.md": LANGUAGE_README.format(name=name, title=title_of(name), command=this_command()),
        "Makefile": MAKEFILE.format(name=name, kind="language"),
        ".github/workflows/verify.yml": WORKFLOW.format(name=name, kind="language", keel=KEEL_REPO),
    }


def write(kind: str, name: str, into: Path, schema: str) -> list[str]:
    """Write the package under `into/<name>`, or refuse a directory that already holds something."""
    checked(kind, name)
    root = into / name
    if root.exists() and any(root.iterdir()):
        raise GenerationError(f"{root} already holds something. A scaffold writes a whole package, so it "
                              f"writes into an empty directory or none at all")
    files = extension_files(name, schema) if kind == "extension" else language_files(name, schema)
    for path, text in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    if kind == "extension":
        (root / "init.py").chmod(0o755)
    return [f"{root / path}" for path in files]


ENTRY_POINT = '''#!/usr/bin/env python3
"""{title}: what `./init --extension {name}` does in a project.

This runs inside a generated or adopted project, which has no slipwai to import — the standard library only,
like every other script under `scripts/`. It is held to the six obligations, and each one below is marked
where it is met so that a change can see what it is breaking.
"""
from __future__ import annotations

import sys
from pathlib import Path

def project_root() -> Path:
    """The project this is installed in: the nearest parent holding `project.json`, falling back to three up.

    Three up is where `scripts/extensions/<key>/init.py` sits, and counting parents is right until somebody
    moves the script or a layout puts the delivery files under a subdirectory — which `layout.delivery`
    does. So the marker is looked for first and the count is only the fallback.
    """
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return here.parents[3]


ROOT = project_root()
BEGIN = "<!-- extension:{name}:begin -->"
END = "<!-- extension:{name}:end -->"
BLOCK = """TODO: what the agent needs to know about {name} — the command it runs, what it answers, when to
reach for it. One short section; this is read on every turn."""


def say(message: str) -> None:
    print(f"[{name}] {{message}}")


def install_tool() -> bool:
    """TODO: install whatever this extension needs, and return whether it is there now.

    Obligation 2, non-fatal: a tool that cannot be installed on this machine is said and returns False. The
    project still works; what this extension adds does not, and the message says how to get it.
    Obligation 5, recovers: the message names the command that fixes it.
    """
    say("TODO: nothing to install yet")
    return True


def project_guidance() -> None:
    """Obligation 3, projects: the block is marker-fenced and replaced whole.

    Obligation 1, idempotent: a second run rewrites the same block rather than appending a second one.
    Obligation 6, merges: everything outside the markers is a person's and is left exactly as it was.
    """
    agents = ROOT / "AGENTS.md"
    text = agents.read_text(encoding="utf-8") if agents.is_file() else ""
    block = f"{{BEGIN}}\\n\\n## {title}\\n\\n{{BLOCK}}\\n\\n{{END}}"
    if BEGIN in text and END in text:
        head, rest = text.split(BEGIN, 1)
        text = head + block + rest.split(END, 1)[1]
    else:
        text = (text.rstrip() + "\\n\\n" + block + "\\n") if text.strip() else block + "\\n"
    agents.write_text(text, encoding="utf-8")
    say("AGENTS.md block written")


def main() -> int:
    if not install_tool():
        return 0  # obligation 2: not fatal to the rest of `./init`
    project_guidance()
    # Obligation 4, gated: if this extension writes an index, a cache or a lock, ship a
    # `scripts/check-{name}.py` that refuses a stale one, and write it from here.
    say("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

README = '''# {title}

A slipwai extension: optional dev tooling a project elects at `./init`.

TODO: what this installs, and what it is for.

## Installing

```sh
{command} extension install <this directory, or its git URL>
```

Then, in a project:

```sh
./init --extension {name}
```

## The six obligations

`{command} extension check .` prints these; the conformance suite runs them.

{obligations}
'''

LANGUAGE_MODULE = '''"""{title}: the backend protocol, as this keel's registry asks it.

The loader imports this module from the package directory and reads `LANGUAGE`. Every member the registry
declares `required` has to be answered here; the rest are optional and fall back to the keel's own.
"""
from __future__ import annotations

from slipwai.registry import Backend, Family, Language

#: TODO: answer the required members. `slipwai conformance --language {name}` lists what is missing and what
#: each one is for, and refuses an answer the generated project would not build with.
BACKEND = Backend(key="{name}", answers={{}})
FAMILY = Family(name="{name}")
LANGUAGE = Language(families=(FAMILY,), backends=(BACKEND,))
'''

LANGUAGE_README = '''# {title}

A slipwai language package: it answers the backend protocol, and `slipwai generate --backend {name}` writes a
skeleton with it.

TODO: what this language and framework are, in two sentences.

## Installing

```sh
{command} language install <this directory>
```

## Checking it

```sh
{command} conformance --language {name}
```

Every required member answered, and the generated project built and tested.
'''


#: The package's own `make`. Three targets, because a publisher has three questions: is it right, what do I
#: ship, and where does it go. Each is the keel's verb with the package's own directory already filled in, so
#: a publisher who forgets the flags still runs the right thing.
MAKEFILE = """# {name}: what a publisher runs. The keel is `slipwai`; install it with `pip install slipwai`.
.DEFAULT_GOAL := check
CHANNEL ?= ../slipwai-index

.PHONY: check release register
check: ## Run the conformance suite this package's kind is held to
	slipwai package check .

release: check ## Build the release file and its index entry under dist/
	slipwai package release . --out dist

register: check ## Build it and write it into a channel checkout (CHANNEL=<directory>)
	slipwai package register . --channel $(CHANNEL)
"""

#: The package's CI: the keel's reusable workflow, called rather than copied, so a fix to it reaches every
#: package. Pinned to no keel version here — the package declares the range in its manifest, and the workflow
#: takes a version when a publisher wants one.
WORKFLOW = """name: verify

on:
  push:
    branches: [main]
    # A tag is what publishes. A green run on `main` is a package that works; it is not a package
    # anybody asked for, and publishing every commit is how a chandlery fills with versions nobody
    # chose. `git tag v1.1.0 && git push --follow-tags` is the whole of releasing.
    tags: ['v*']
  pull_request:
  workflow_dispatch:

jobs:
  conformance:
    uses: {keel}/.github/workflows/package.yml@main
    with:
      package: {name}
      kind: {kind}
      # Where a tag publishes to. Empty publishes nowhere, which is right for a fork.
      channel: ''
      # Which keel to prove against: a bare version is one on PyPI, anything else is passed to pip as it
      # stands. Empty installs `slipwai`, which is right once the version you need is published.
      keel: ''
    # A token that may open a pull request on that channel. Without it a tag still builds the release
    # and attaches it to itself, and `slipwai package register` finishes the job by hand — so a fork
    # needs no credential and a package nobody owns can still be proved.
    secrets:
      chandlery_token: ${{{{ secrets.CHANDLERY_TOKEN }}}}
"""
