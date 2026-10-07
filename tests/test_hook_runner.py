"""`scripts/extensions/hooks.py`: electing the hooks, and firing a point without ever failing the rung.

The runner ships inside a generated project, so it is run here the way a project runs it — as a script, with
python3, against a directory laid out the way a project is — rather than imported. It is the toolkit side of
`src/slipwai/hooks.py`, which declares the points; this proves what happens at one.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT

RUNNER = TOOLKIT_ROOT / "scripts/extensions/hooks.py"
AVAILABLE = {
    "noisy": {"after-stage": {"run": "hook.py", "budget": "30s"}},
    "picky": {"after-stage": {"run": "hook.py", "budget": "30s", "stages": ["implement"]}},
    "slow": {"boundary": {"run": "hook.py", "budget": "1s"}},
}


class RunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        self.scripts = self.root / "scripts/extensions"
        self.scripts.mkdir(parents=True)
        (self.scripts / "hooks.py").write_text(RUNNER.read_text(encoding="utf-8"), encoding="utf-8")
        (self.scripts / "available.json").write_text(json.dumps(AVAILABLE), encoding="utf-8")

    def extension(self, key: str, body: str) -> None:
        place = self.scripts / key
        place.mkdir(parents=True, exist_ok=True)
        (place / "hook.py").write_text(body, encoding="utf-8")

    def invoke(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.scripts / "hooks.py"), *argv],
                              capture_output=True, text=True, cwd=self.root)

    def registry(self) -> dict:
        return json.loads((self.root / ".slipwai/hooks.json").read_text(encoding="utf-8"))

    def test_electing_writes_only_what_was_elected(self) -> None:
        self.invoke("--elect", "noisy")
        points = self.registry()["points"]
        self.assertEqual([one["extension"] for one in points["after-stage"]], ["noisy"])
        self.assertNotIn("boundary", points)

    def test_electing_twice_writes_the_same_registry(self) -> None:
        self.invoke("--elect", "noisy", "picky")
        first = self.registry()
        self.invoke("--elect", "picky", "noisy")
        self.assertEqual(first, self.registry())

    def test_a_hook_that_fails_is_a_line_and_not_a_failed_rung(self) -> None:
        """The whole rule: a hook is a second belt, and a second belt cannot stop the loop it was added to."""
        self.extension("noisy", "import sys\nprint('it went wrong')\nsys.exit(3)\n")
        self.invoke("--elect", "noisy")
        done = self.invoke("after-stage", "--stage", "implement")
        self.assertEqual(done.returncode, 0)
        self.assertIn("hook noisy after-stage", done.stderr)
        self.assertIn("it went wrong", done.stderr)

    def test_a_hook_over_its_budget_is_ended_and_said(self) -> None:
        self.extension("slow", "import time\ntime.sleep(30)\n")
        self.invoke("--elect", "slow")
        done = self.invoke("boundary")
        self.assertEqual(done.returncode, 0)
        self.assertIn("budget", done.stderr)

    def test_a_hook_whose_script_is_not_there_is_said_rather_than_raised(self) -> None:
        self.invoke("--elect", "noisy")
        done = self.invoke("after-stage", "--stage", "implement")
        self.assertEqual(done.returncode, 0)
        self.assertIn("is not in this project", done.stderr)

    def test_a_hook_that_names_stages_is_skipped_at_the_others(self) -> None:
        self.extension("picky", "import sys\nsys.exit(1)\n")
        self.invoke("--elect", "picky")
        quiet = self.invoke("after-stage", "--stage", "review")
        self.assertEqual((quiet.returncode, quiet.stderr), (0, ""))
        loud = self.invoke("after-stage", "--stage", "implement")
        self.assertIn("hook picky", loud.stderr)

    def test_a_hook_is_given_the_rung_in_its_environment(self) -> None:
        self.extension("noisy", "import os, sys\nsys.exit(0 if os.environ.get('SLIPWAI_SLICE') == 'ORD-01' else 9)\n")
        self.invoke("--elect", "noisy")
        done = self.invoke("after-stage", "--stage", "implement", "--slice", "ORD-01")
        self.assertEqual(done.stderr, "")

    def test_a_point_nothing_is_attached_to_does_nothing_at_all(self) -> None:
        self.invoke("--elect", "noisy")
        done = self.invoke("before-merge")
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    def test_no_registry_at_all_is_not_an_error(self) -> None:
        """A project that elected nothing has no registry, and every point still fires into nothing."""
        done = self.invoke("after-stage", "--stage", "implement")
        self.assertEqual((done.returncode, done.stderr), (0, ""))


class BudgetTest(unittest.TestCase):
    def test_a_budget_nobody_can_parse_does_not_stop_the_hook_running(self) -> None:
        import importlib.util
        specification = importlib.util.spec_from_file_location("hook_runner", RUNNER)
        assert specification and specification.loader
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        self.assertEqual(module.seconds("2m"), 120.0)
        self.assertEqual(module.seconds("45"), 45.0)
        self.assertEqual(module.seconds("whenever"), 30.0)


if __name__ == "__main__":
    unittest.main()
