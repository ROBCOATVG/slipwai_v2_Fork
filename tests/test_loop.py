"""The loop, end to end, in a project the keel generated.

Every other suite proves one link. This drives the chain: generate a project, write a model into it, render
the chart, run its gate, run a captain over it with a stand-in for `/drive`, carry the lines with the
harbourmaster, and read the board back.

It exists because three faults were found by hand in ten minutes doing exactly this, and none of them could
have been found by the other suites — each was a *disagreement between two things* that are tested apart:
the renderer against its own gate, the model schema against the gate's demands, the renderer against a
project that has a web app as well as a service.

The claim it is really here to hold is the one version 2 rests on: **a sibling is cleared by a mark being
set, not by anything merging.** If that ever stops being true the method has no parallelism in it, and
nothing else in the suite would notice.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages

REPOSITORY = Path(__file__).resolve().parents[1]
TOY = "toy-plain"
#: Two streams, and the second steers by a mark the first sets. The whole point in six lines of YAML.
SLICES = """\
slices:
  - id: ORD-01
    name: Place an order
    capability: Ordering and billing
    context: ordering
    pattern: state-change
    status: planned
    stream: order-{orderId}
    frames:
      - type: ui
        name: OrderForm
      - type: cmd
        name: PlaceOrder
      - type: evt
        name: OrderPlaced
  - id: BIL-01
    name: Charge for an order
    capability: Ordering and billing
    context: billing
    pattern: automation
    status: planned
    materialisation: async
    reads: [OrderPlaced]
    stream: invoice-{invoiceId}
    frames:
      - type: rmo
        name: UnbilledOrders
      - type: pcr
        name: Biller
      - type: cmd
        name: ChargeOrder
      - type: evt
        name: OrderCharged
"""
#: A stand-in for `/drive`: it writes what the chart says this slice sets, and nothing it does not.
DRIVE = '''\
import sys, json, pathlib, datetime, yaml
slice_id, fairway = sys.argv[1], sys.argv[2]
chart = yaml.safe_load(pathlib.Path("specs/model/chart.yaml").read_text(encoding="utf-8"))
sets = ((chart.get("slices") or {}).get(slice_id) or {}).get("sets") or []
path = pathlib.Path(".slipwai/logs/model") / (fairway + ".jsonl")
path.parent.mkdir(parents=True, exist_ok=True)
def line(**fields):
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"v": 1, "t": now, **fields}) + "\\n")
for mark in sets:
    line(kind="mark-set", fairway=fairway, slice=slice_id, mark=mark)
line(kind="heartbeat", fairway=fairway, tokens=7)
line(kind="demo", fairway=fairway, slice=slice_id, verdict="accepted")
'''


def has_yaml() -> bool:
    try:
        import yaml  # type: ignore[import-untyped] # noqa: F401
    except ImportError:
        return False
    return True


@unittest.skipUnless(checkout_packages.installed("toy"), "needs the toy package: slice 3.8")
@unittest.skipUnless(has_yaml(), "the chart renderer and the stand-in both read YAML")
class LoopTest(unittest.TestCase):
    """One generation, driven. Generated once for the class: it is the slow part, and five subclasses
    would be five generations and five copies of every test."""

    project: Path
    scratch: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.scratch = tempfile.TemporaryDirectory()
        done = subprocess.run(
            [sys.executable, "-m", "slipwai", "generate", "demo", "--backend", TOY,
             "--frontend", "none", "--target", "none", "--profile", "event-modelling",
             "--output", cls.scratch.name],
            cwd=REPOSITORY, capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(REPOSITORY / "src"),
                 "SLIPWAI_LANGUAGES": str(checkout_packages.PACKAGES)},
        )
        if done.returncode != 0:
            raise AssertionError(done.stdout + done.stderr)
        cls.project = Path(cls.scratch.name) / "demo"
        model = cls.project / "docs/event-model/model.yaml"
        held = model.read_text(encoding="utf-8")
        assert "slices: []" in held, "the seeded model no longer ends on an empty slice list"
        model.write_text(held.replace("slices: []\n", SLICES), encoding="utf-8")
        (cls.project / "drive-stand-in.py").write_text(DRIVE, encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.scratch.cleanup()

    def setUp(self) -> None:
        """The generation is shared because it is slow; the run is not, because it is the thing being
        tested. A test that inherited the last one's logs would be a test whose result depends on the
        order they ran in — which is how a suite goes green on a claim nobody is making any more."""
        import shutil
        shutil.rmtree(self.project / ".slipwai", ignore_errors=True)
        (self.project / "specs/model/chart.yaml").unlink(missing_ok=True)

    def run_in(self, *argv: str, drive: bool = False) -> subprocess.CompletedProcess:
        env = {**os.environ}
        if drive:
            env["SLIPWAI_DRIVE"] = f"{sys.executable} {self.project / 'drive-stand-in.py'}"
        return subprocess.run([sys.executable, *argv], cwd=self.project, capture_output=True, text=True,
                              env=env, timeout=180)

    def entries(self, fairway: str) -> list[dict]:
        path = self.project / f".slipwai/logs/model/{fairway}.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def kinds(self, fairway: str) -> list[str]:
        return [entry["kind"] for entry in self.entries(fairway)]


    def test_the_chart_renders_from_the_model(self) -> None:
        done = self.run_in("scripts/event-model/chart.py")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("2 slices", done.stdout)

    def test_and_the_chart_gate_accepts_what_the_renderer_wrote(self) -> None:
        """The pairing rule. A generator whose output fails its own gate is the worst of the two."""
        self.run_in("scripts/event-model/chart.py")
        done = self.run_in("scripts/check-chart.py")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_single_service_project_still_gets_its_fairways(self) -> None:
        """One service and a web app is two deployables and nothing to decide, and that left the chart
        with no fairways at all and every slice naming one it had not got."""
        self.run_in("scripts/event-model/chart.py")
        chart = (self.project / "specs/model/chart.yaml").read_text(encoding="utf-8")
        self.assertIn("billing:", chart)
        self.assertIn("ordering:", chart)

    def test_only_the_slice_that_waits_on_nothing_may_start(self) -> None:
        self.run_in("scripts/event-model/chart.py")
        done = self.run_in("scripts/agents/clearance.py")
        self.assertIn("ORD-01", done.stdout)
        self.assertNotIn("BIL-01", done.stdout)

    def test_a_sibling_is_cleared_by_a_mark_being_set_and_not_by_a_merge(self) -> None:
        """The claim the whole method rests on. Nothing merges in this test, and billing still clears."""
        self.run_in("scripts/event-model/chart.py")
        self.run_in("scripts/agents/captain.py", "ordering", "--once", drive=True)
        self.run_in("scripts/agents/harbourmaster.py", "--once", "--no-fetch")
        done = self.run_in("scripts/agents/clearance.py")
        self.assertIn("BIL-01", done.stdout)
        self.assertNotIn("merged", "".join(self.kinds("ordering")))

    def test_a_captain_claims_dispatches_and_asks_for_the_merge(self) -> None:
        self.run_in("scripts/event-model/chart.py")
        done = self.run_in("scripts/agents/captain.py", "ordering", "--once", drive=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.kinds("ordering")[0], "claimed")
        self.assertIn("mark-set", self.kinds("ordering"))
        self.assertIn("request", self.kinds("ordering"))

    def test_it_holds_no_credential_and_the_merge_is_asked_for(self) -> None:
        """A berth with a token in it is a sandbox with a way out."""
        self.run_in("scripts/event-model/chart.py")
        self.run_in("scripts/agents/captain.py", "ordering", "--once", drive=True)
        asked = [one for one in self.entries("ordering") if one["kind"] == "request"]
        self.assertEqual([one["what"] for one in asked], ["merge"])

    def test_a_stream_named_by_its_slice_prefix_is_told_it_is_the_context(self) -> None:
        self.run_in("scripts/event-model/chart.py")
        done = self.run_in("scripts/agents/captain.py", "ORD", "--once", drive=True)
        self.assertIn("no slices", done.stdout)

    def test_it_carries_a_mark_and_answers_the_request(self) -> None:
        self.run_in("scripts/event-model/chart.py")
        self.run_in("scripts/agents/captain.py", "ordering", "--once", drive=True)
        self.run_in("scripts/agents/harbourmaster.py", "--once", "--no-fetch")
        harbour = (self.project / ".slipwai/logs/harbour.jsonl").read_text(encoding="utf-8")
        kinds = [json.loads(line)["kind"] for line in harbour.splitlines() if line.strip()]
        self.assertIn("mark-set", kinds)
        self.assertIn("granted", kinds)

    def test_the_board_folds_what_the_run_wrote(self) -> None:
        self.run_in("scripts/event-model/chart.py")
        self.run_in("scripts/agents/captain.py", "ordering", "--once", drive=True)
        done = subprocess.run(
            [sys.executable, "-m", "slipwai", "fleet", "--root", str(self.project)],
            cwd=REPOSITORY, capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(REPOSITORY / "src"),
                 "SLIPWAI_LANGUAGES": str(checkout_packages.PACKAGES)}, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("ordering", done.stdout)
        self.assertIn("ORD-01", done.stdout)

    def test_the_run_state_overlay_is_folded_from_the_same_lines(self) -> None:
        self.run_in("scripts/event-model/chart.py")
        self.run_in("scripts/agents/captain.py", "ordering", "--once", drive=True)
        done = self.run_in("scripts/agents/run-state.py", "--print")
        held = json.loads(done.stdout)
        self.assertEqual(held["slices"]["ORD-01"]["state"], "demoed")
        self.assertIn("OrderPlaced", held["marks"])


if __name__ == "__main__":
    unittest.main()
