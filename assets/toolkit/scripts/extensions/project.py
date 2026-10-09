#!/usr/bin/env python3
"""Re-project elected extension guidance without rerunning extension setup.

The projection itself is the `project` point of `hooks.py`'s closed set, fired through the registry like
every other point — which is what slice 6.1e closed. Until then this script imported each extension's
`init.py` and called a function called `project_guidance()` by name, so an extension that declared a
different script at that point was ignored: installed, valid, and silently never run.

What is still read from the module is `GUIDANCE`, and that is *data* rather than a point — the canonical
text of the block, which `--check` compares against what is in `AGENTS.md`. A drift check has to know what
the block should say, and a subprocess that writes it cannot answer that question.
"""
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

sys.dont_write_bytecode = True
from guidance import ROOT, adopted_extensions, canonical_block, installed_block

HERE = Path(__file__).resolve().parent
HOOKS = HERE / "hooks.py"


def extension_module(key: str) -> ModuleType:
    script = HERE / key / "init.py"
    if not script.is_file():
        raise ValueError(f"{key}: elected extension has no {script.relative_to(ROOT)}")
    spec = importlib.util.spec_from_file_location(f"slipwai_extension_{key.replace('-', '_')}", script)
    if spec is None or spec.loader is None:
        raise ValueError(f"{key}: cannot load {script.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fire_project() -> list[str]:
    """The `project` point, through the registry. Never fatal, as a hook never is: `hooks.py` exits 0
    whatever a hook did, and what a failure produces is a `hook` line on stderr naming the extension."""
    try:
        subprocess.run([sys.executable, str(HOOKS), "project"], cwd=ROOT, check=False)
    except OSError as error:
        return [f"the project point could not be fired ({type(error).__name__})"]
    return []


def project(check: bool) -> list[str]:
    findings: list[str] = []
    try:
        adopted = adopted_extensions(persist_legacy=not check)
    except (OSError, ValueError) as error:
        return [str(error)]
    if not check:
        return fire_project()
    for key in adopted:
        try:
            # `GUIDANCE` is the block's canonical text, read as data: the drift check has to know what the
            # block should say, which is not something the point that writes it can be asked.
            canonical = canonical_block(key, extension_module(key).GUIDANCE)
            if installed_block(key) != canonical:
                findings.append(
                    f"AGENTS.md: the {key} extension block has drifted; run `make agents` "
                    "or `slipwai migrate`"
                )
        except (AttributeError, OSError, ValueError) as error:
            findings.append(str(error))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    findings = project(arguments.check)
    if findings:
        print("\n".join(f"check-extensions: {finding}" for finding in findings), file=sys.stderr)
        return 1
    adopted = adopted_extensions(persist_legacy=False)
    if not adopted:
        print("check-extensions: no extension elected; nothing to project")
    elif arguments.check:
        print(f"check-extensions: {len(adopted)} elected extension block(s) match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
