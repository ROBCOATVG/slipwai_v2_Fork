"""`./init`'s word about the language packages this project records and this machine has not installed.

A clone of a project made with `go` 1.4.0 is worked on by somebody whose slipwai may have no `go` at all — or no
slipwai: `make verify` needs none, since a generated project's gate never runs the keel. So `./init`
only *says* so, with the command that installs them, and never fails for it. It reads `generator.languages`
(ADR 0005) with `python3`, and looks for each package where slipwai does, `${SLIPWAI_LANGUAGES:-~/.slipwai/languages}`.
It names bare `slipwai`: the clone has no factory checkout to point a path at. A 1.x project records nothing,
an adopted one records `{}`, and a machine with no `python3` is told nothing here: nothing is guessed.
"""
from __future__ import annotations

LANGUAGES_CHECK = r"""
# The language packages project.json records (generator.languages) that this machine has not installed: named,
# with the command that installs them. Never fatal — `make verify` needs none of them.
if command -v python3 >/dev/null 2>&1; then
  python3 - <<'SLIPWAI_LANGUAGES_CHECK' || true
import json, os, pathlib, re, sys
try:
    generator = json.loads(pathlib.Path("project.json").read_text()).get("generator") or {}
    recorded = generator.get("languages") or {}
except (OSError, ValueError, AttributeError):
    recorded = {}
if not isinstance(recorded, dict):
    print("project.json's generator.languages is not a map of package names; nothing is checked.", file=sys.stderr)
    recorded = {}
where = pathlib.Path(os.environ.get("SLIPWAI_LANGUAGES") or pathlib.Path.home() / ".slipwai/languages")
slug = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
named = [name for name in recorded if isinstance(name, str) and slug.fullmatch(name)]
for name in recorded:
    if name not in named:
        print("project.json's generator.languages has an entry that is not a package name, skipped: "
              + ascii(name)[:60], file=sys.stderr)
missing = [name for name in named if not (where / name / "VERSION").is_file()]
if missing:
    print("This project was made with language packages that are not installed in " + str(where) + ": "
          + ", ".join(missing) + ". To add a service or migrate it here, install them:\n"
          + "  slipwai language install " + " ".join(missing) + "\n"
          + "make verify works without them.", file=sys.stderr)
SLIPWAI_LANGUAGES_CHECK
fi
"""
