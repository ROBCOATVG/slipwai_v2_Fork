"""The six obligations, run against packages written to break exactly one of them each.

A suite that only ever sees a passing package proves nothing about what it would refuse, so every check here
has a package that fails it and a package that does not — and the passing one is the scaffold, because what
`slipwai package new` writes has to meet the list the same command prints.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import package_new
from slipwai.conformance.extension import check

CORE = "9.0"
FENCE = ('BEGIN = "<!-- extension:{key}:begin -->"\nEND = "<!-- extension:{key}:end -->"\n')


def package(root: Path, key: str, body: str, ignore: str | None = None) -> Path:
    place = root / key
    place.mkdir(parents=True)
    manifest = {"key": key, "name": key.title(), "description": "A fake", "kind": "extension",
                "core": ">=9.0,<10", "hooks": {"init": "init.py"}}
    if ignore:
        manifest["ignore"] = ignore
    (place / "extension.json").write_text(json.dumps(manifest), encoding="utf-8")
    (place / "init.py").write_text(body, encoding="utf-8")
    return place


PROJECTS = FENCE + '''
import pathlib
agents = pathlib.Path("AGENTS.md")
text = agents.read_text(encoding="utf-8")
block = BEGIN.format(key="{key}") + "\\n\\nguidance\\n\\n" + END.format(key="{key}")
if BEGIN.format(key="{key}") in text:
    head, rest = text.split(BEGIN.format(key="{key}"), 1)
    text = head + block + rest.split(END.format(key="{key}"), 1)[1]
else:
    text = text.rstrip() + "\\n\\n" + block + "\\n"
agents.write_text(text, encoding="utf-8")
'''


class SuiteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())

    def test_the_scaffold_passes_all_six(self) -> None:
        """`package new` writes the publisher's first package. One that fails the list is a broken lesson."""
        package_new.write("extension", "thing", self.area, CORE)
        report = check(self.area / "thing")
        self.assertTrue(report.passed, report.findings)

    def test_an_entry_point_that_appends_every_run_fails_idempotent(self) -> None:
        body = PROJECTS.format(key="loud").replace("if BEGIN.format(key=\"loud\") in text:",
                                                   "if False:")
        package(self.area, "loud", body)
        report = check(self.area / "loud")
        self.assertTrue(report.findings["idempotent"])

    def test_an_entry_point_that_exits_non_zero_with_no_tools_fails_non_fatal(self) -> None:
        body = PROJECTS.format(key="brittle") + '\nimport shutil, sys\nsys.exit(0 if shutil.which("git") else 1)\n'
        package(self.area, "brittle", body)
        report = check(self.area / "brittle")
        self.assertTrue(report.findings["non-fatal"])
        self.assertIn("PATH", report.findings["non-fatal"][0])

    def test_an_unfenced_block_fails_projects(self) -> None:
        package(self.area, "bare", 'import pathlib\n'
                'pathlib.Path("AGENTS.md").write_text("# A project\\n\\nguidance\\n", encoding="utf-8")\n')
        report = check(self.area / "bare")
        self.assertTrue(report.findings["projects"])

    def test_overwriting_what_a_person_wrote_fails_merges(self) -> None:
        package(self.area, "rude", 'import pathlib\n'
                'pathlib.Path("AGENTS.md").write_text("mine now\\n", encoding="utf-8")\n')
        report = check(self.area / "rude")
        self.assertTrue(report.findings["merges"])

    def test_leaving_state_with_no_gate_fails_gated(self) -> None:
        package(self.area, "stateful", PROJECTS.format(key="stateful"), ignore=".stateful/\n")
        report = check(self.area / "stateful")
        self.assertTrue(report.findings["gated"])

    def test_declaring_a_check_hook_satisfies_gated(self) -> None:
        place = package(self.area, "checked", PROJECTS.format(key="checked"), ignore=".checked/\n")
        manifest = json.loads((place / "extension.json").read_text(encoding="utf-8"))
        manifest["hooks"]["check"] = "hooks/check.py"
        (place / "extension.json").write_text(json.dumps(manifest), encoding="utf-8")
        (place / "hooks").mkdir()
        (place / "hooks/check.py").write_text("", encoding="utf-8")
        self.assertEqual(check(place).findings["gated"], [])

    def test_a_problem_reported_with_no_command_fails_recovers(self) -> None:
        body = PROJECTS.format(key="terse") + '\nprint("the tool could not be installed")\n'
        package(self.area, "terse", body)
        report = check(self.area / "terse")
        self.assertTrue(report.findings["recovers"])

    def test_the_same_problem_with_the_command_passes_recovers(self) -> None:
        body = PROJECTS.format(key="kind") + '\nprint("the tool could not be installed; run `brew install it`")\n'
        package(self.area, "kind", body)
        self.assertEqual(check(self.area / "kind").findings["recovers"], [])

    def test_an_entry_point_the_package_does_not_ship_is_not_run_rather_than_failed(self) -> None:
        place = package(self.area, "absent", "")
        (place / "init.py").unlink()
        report = check(place)
        self.assertEqual(report.findings, {})
        self.assertEqual(len(report.not_run), 6)
        self.assertIn("init.py", report.not_run["idempotent"])
        self.assertTrue(report.passed, "nothing was checked, so nothing failed; the report says so instead")


if __name__ == "__main__":
    unittest.main()
