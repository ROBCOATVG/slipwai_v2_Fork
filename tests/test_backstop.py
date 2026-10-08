"""The release backstop: every published package run against the keel about to ship.

The keel's own gate proves the conformance suite works. Each package proves itself against a pinned keel.
Neither asks the question a release has to answer — *does this keel still work with what is already out
there?* — and a keel that ran every package's gate on every commit would be a keel nobody could change
without them, which is the coupling the packages were split out to remove.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import ROOT

WORKFLOW = ROOT / ".github/workflows/backstop.yml"
SCRIPT = ROOT / "scripts/backstop-packages.py"
LANGUAGE = {"name": "toy", "core": ">=9.0,<10", "family": "toy",
            "backends": {"toy-plain": {"label": "Toy", "targets": ["none"], "options": {"http": ["none"]}}}}


class WorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_it_runs_on_a_tag_and_never_on_every_commit(self) -> None:
        """A keel whose gate checks seven packages is a keel nobody can change without them."""
        self.assertIn("tags: ['v*']", self.text)
        self.assertNotIn("pull_request:", self.text)

    def test_it_installs_the_keel_from_this_checkout_and_not_from_the_registry(self) -> None:
        """The point is the version that has not been published — the one no package has met."""
        self.assertIn("pip install --disable-pip-version-check ./keel", self.text)

    def test_the_package_list_comes_from_the_channel_and_not_from_this_file(self) -> None:
        """A list in a workflow is wrong the day somebody publishes a seventh and nobody remembers it."""
        self.assertIn("scripts/backstop-packages.py", self.text)

    def test_nothing_checked_refuses_the_release(self) -> None:
        """A matrix job skipped because nothing was listed is a green meaning "nothing was checked"."""
        self.assertIn('if [ "$LISTED" = "[]" ]', self.text)
        self.assertIn("refuse a release that checked nothing", self.text)

    def test_the_matrix_does_not_stop_at_the_first_failure(self) -> None:
        """One package failing is a thing to know about; the other six are too."""
        self.assertIn("fail-fast: false", self.text)

    def test_the_package_directory_is_read_from_the_keel_and_not_written_in_yaml(self) -> None:
        """It moves in 8.3, and a path in a YAML file would not move with it."""
        self.assertIn("needs.listed.outputs.directory", self.text)
        self.assertNotIn(".slipwai/packages", self.text)


class NoPerCommitPackageJobTest(unittest.TestCase):
    """Version 1's root matrix regenerated every language's variants on every commit, which is the
    coupling this whole division exists to remove. Nothing per-commit may read a package."""

    def test_the_keel_s_own_gate_installs_no_package(self) -> None:
        said = (ROOT / ".github/workflows/verify.yml").read_text(encoding="utf-8")
        for forbidden in ("slipwai install", "slipwai language install", "slipwai.matrix",
                          "submodule update"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, said)

    def test_and_the_only_workflow_that_does_runs_on_a_tag(self) -> None:
        place = ROOT / ".github/workflows"
        for path in sorted(place.glob("*.yml")):
            said = path.read_text(encoding="utf-8")
            if "slipwai.matrix" not in said:
                continue
            with self.subTest(workflow=path.name):
                # package.yml is called by a package's own repository and never triggered here; backstop
                # runs on a tag. Neither is a per-commit job of this repository's.
                self.assertTrue("workflow_call:" in said or "tags: ['v*']" in said, path.name)


class ListingTest(unittest.TestCase):
    def run_it(self, **environment: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True,
                              env={**os.environ, **environment})

    def output(self, done: subprocess.CompletedProcess) -> dict[str, str]:
        return dict(line.split("=", 1) for line in done.stdout.splitlines() if "=" in line)

    def channel(self, root: Path, names: list[str]) -> str:
        place = root / "slipwai-languages"
        place.mkdir(parents=True)
        place.joinpath("index.json").write_text(json.dumps({
            "index": 2,
            "packages": {name: [{"version": "1.0.0", "file": f"{name}.tar.gz", "sha256": "0" * 64,
                                 "kind": "language",
                                 "language": {**LANGUAGE, "name": name, "family": name}}]
                         for name in names},
        }), encoding="utf-8")
        return root.as_uri()

    def test_it_lists_what_the_channel_offers(self) -> None:
        base = self.channel(Path(tempfile.mkdtemp()), ["go", "rust"])
        done = self.run_it(ASKED="", SLIPWAI_CHANDLERY=base, SLIPWAI_INDEX=base)
        self.assertEqual(json.loads(self.output(done)["packages"]), ["go", "rust"])

    def test_a_channel_that_cannot_be_reached_lists_nothing_and_says_why_once(self) -> None:
        """Once: wrapping a whole message in another says "could not be reached (could not be reached (…))"."""
        nowhere = (Path(tempfile.mkdtemp()) / "nothing").as_uri()
        done = self.run_it(ASKED="", SLIPWAI_CHANDLERY=nowhere, SLIPWAI_INDEX=nowhere)
        self.assertEqual(json.loads(self.output(done)["packages"]), [])
        self.assertEqual(done.stderr.count("could not be reached"), 1)

    def test_a_person_may_name_them_instead(self) -> None:
        done = self.run_it(ASKED="go rust")
        self.assertEqual(json.loads(self.output(done)["packages"]), ["go", "rust"])

    def test_it_says_where_the_packages_will_be_installed(self) -> None:
        done = self.run_it(ASKED="go")
        self.assertIn("directory", self.output(done))

    def test_it_never_fails_so_the_verdict_job_is_what_refuses(self) -> None:
        """One place decides whether a release is refused, and it is the job that says so out loud."""
        nowhere = (Path(tempfile.mkdtemp()) / "nothing").as_uri()
        self.assertEqual(self.run_it(ASKED="", SLIPWAI_CHANDLERY=nowhere,
                                     SLIPWAI_INDEX=nowhere).returncode, 0)


class MessageTest(unittest.TestCase):
    def test_an_unreachable_index_carries_its_reason_apart_from_its_sentence(self) -> None:
        from slipwai.language_index import Unreachable
        error = Unreachable("https://x.invalid/index.json", "nothing is published there")
        self.assertEqual(error.reason, "nothing is published there")
        self.assertIn("could not be reached", str(error))


if __name__ == "__main__":
    unittest.main()


class TagPublishTest(unittest.TestCase):
    """A tag publishes; a green run on main does not. A green run is a package that works, and that is
    not a package anybody asked for — publishing every commit is how a chandlery fills with versions
    nobody chose."""

    def setUp(self) -> None:
        self.text = (ROOT / ".github/workflows/package.yml").read_text(encoding="utf-8")

    def test_the_publish_job_runs_on_a_tag_and_on_nothing_else(self) -> None:
        self.assertIn("startsWith(github.ref, 'refs/tags/v')", self.text)

    def test_it_waits_for_conformance(self) -> None:
        """A package that does not pass its own suite is not one to put in front of anybody."""
        self.assertIn("needs: conformance", self.text)

    def test_the_release_is_built_in_ci_and_not_taken_from_a_machine(self) -> None:
        """A release file nobody can reproduce is a release file nobody can check, and this is the one
        place the bytes and the tag are known to belong to each other."""
        self.assertIn("slipwai package release .", self.text)

    def test_a_channel_it_was_not_given_publishes_nowhere(self) -> None:
        """Which is right for a fork, and for anyone proving a package they do not own."""
        self.assertIn("inputs.channel != ''", self.text)

    def test_without_a_token_it_says_so_and_leaves_the_release_attached(self) -> None:
        """Nothing in a package repository has ever held a credential for somebody else's."""
        self.assertIn("no chandlery_token", self.text)
        self.assertIn("slipwai package register", self.text)

    def test_the_token_is_a_secret_and_never_required(self) -> None:
        self.assertIn("chandlery_token:", self.text)
        self.assertIn("required: false", self.text)

    def test_publishing_is_a_pull_request_rather_than_a_push(self) -> None:
        """The channel's own gate runs on it and a person merges it, which is the whole of the path a
        contributor from outside follows too."""
        self.assertIn("gh pr create", self.text)
        self.assertNotIn("git push -u origin main", self.text)

    def test_the_scaffold_wires_a_tag_to_it(self) -> None:
        import tempfile
        from pathlib import Path as P

        from slipwai import package_new
        area = P(tempfile.mkdtemp())
        package_new.write("extension", "lens", area, "9.0")
        said = (area / "lens/.github/workflows/verify.yml").read_text(encoding="utf-8")
        self.assertIn("tags: ['v*']", said)
        self.assertIn("chandlery_token", said)
        self.assertIn("channel: ''", said)
