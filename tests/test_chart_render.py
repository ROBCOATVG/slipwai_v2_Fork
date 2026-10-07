"""`make chart` on the event profile: the chart derived from the model, never written beside it.

The model already names each slice's context and service, types the events each slice produces, and says
what each slice reads. So the chart is not authored here, it is rendered — and `check-chart` refuses a
committed chart that has drifted from the model, the way `make check-drawio` holds the committed canvas.
Two answers to one question diverge silently, because nothing else reads both.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "assets/toolkit/scripts/check-chart.py"

MODEL = """
version: 1
slices:
  - id: PlaceOrder
    context: ordering
    service: orders
    capability: place-an-order
    pattern: state-change
    frames:
      - {type: ui, name: Cart}
      - {type: cmd, name: PlaceOrder}
      - {type: evt, name: OrderPlaced}
  - id: RaiseInvoice
    context: billing
    service: billing
    capability: bill-an-order
    pattern: automation
    reads: [OrderPlaced]
    frames:
      - {type: rmo, name: PlacedOrders}
      - {type: pcr, name: Invoicer}
      - {type: cmd, name: RaiseInvoice}
      - {type: evt, name: InvoiceRaised}
"""
MANIFEST = """
{"deployables": {"orders": {"kind": "service", "path": "apps/orders", "contexts": ["ordering"]},
                 "billing": {"kind": "service", "path": "apps/billing", "contexts": ["billing", "tax"]}}}
"""


class RenderedChartTest(unittest.TestCase):
    """`make chart` on the event profile: the chart is derived from the model, never written beside it."""

    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        for directory in ("scripts/event-model", "docs/event-model", "specs/ordering/slices"):
            (self.tree / directory).mkdir(parents=True)
        shutil.copy(ROOT / "assets/toolkit/scripts/event-model/chart.py", self.tree / "scripts/event-model/chart.py")
        shutil.copy(GATE, self.tree / "scripts/check-chart.py")
        (self.tree / "docs/event-model/model.yaml").write_text(textwrap.dedent(MODEL).lstrip(), encoding="utf-8")
        (self.tree / "project.json").write_text(textwrap.dedent(MANIFEST).lstrip(), encoding="utf-8")

    def render(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "scripts/event-model/chart.py"], cwd=self.tree,
                              capture_output=True, text=True, check=False)

    def chart(self) -> dict:
        import yaml  # type: ignore[import-untyped]
        loaded = yaml.safe_load((self.tree / "specs/ordering/chart.yaml").read_text(encoding="utf-8"))
        assert isinstance(loaded, dict)
        return loaded

    def test_the_model_renders_a_chart_the_gate_accepts(self) -> None:
        self.assertEqual(self.render().returncode, 0)
        done = subprocess.run([sys.executable, "scripts/check-chart.py"], cwd=self.tree,
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_fairway_per_context_owning_what_that_context_holds(self) -> None:
        """A service with one context owns all of it; one holding several owns the context's own directory."""
        self.render()
        fairways = self.chart()["fairways"]
        self.assertEqual(sorted(fairways), ["billing", "ordering"])
        self.assertEqual(fairways["ordering"]["owns"], ["apps/orders/**"])
        self.assertEqual(fairways["billing"]["owns"], ["apps/billing/src/billing/**"])

    def test_an_event_mark_points_at_the_model_rather_than_a_generated_schema(self) -> None:
        """Generating JSON Schema would mean inventing a type mapping, and that mapping would be the
        contract every other fairway steers by — a type system invented in a renderer, by nobody."""
        self.render()
        self.assertEqual(self.chart()["marks"]["OrderPlaced"],
                         {"kind": "event", "schema": "docs/event-model/model.yaml#OrderPlaced"})

    def test_what_a_slice_sets_and_steers_by_comes_from_its_frames_and_its_reads(self) -> None:
        self.render()
        slices = self.chart()["slices"]
        self.assertEqual(slices["PlaceOrder"]["sets"], ["OrderPlaced"])
        self.assertEqual(slices["PlaceOrder"]["steers_by"], [])
        self.assertEqual(slices["RaiseInvoice"]["steers_by"], ["OrderPlaced"])
        self.assertEqual(slices["RaiseInvoice"]["capability"], "bill-an-order")

    def test_rendering_twice_writes_the_same_chart(self) -> None:
        """A chart that churns on every render is a chart nobody can read a diff of."""
        self.render()
        first = (self.tree / "specs/ordering/chart.yaml").read_text(encoding="utf-8")
        self.render()
        self.assertEqual(first, (self.tree / "specs/ordering/chart.yaml").read_text(encoding="utf-8"))

    def test_a_chart_edited_by_hand_is_refused_against_the_model(self) -> None:
        """The model is the source of truth on this profile, so the chart is derived and never authored."""
        self.render()
        path = self.tree / "specs/ordering/chart.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("bill-an-order", "something-else"),
                        encoding="utf-8")
        done = subprocess.run([sys.executable, "scripts/check-chart.py"], cwd=self.tree,
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("disagree(s) with docs/event-model/model.yaml", done.stderr)
        self.assertIn("run `make chart`", done.stderr)

    def test_a_project_with_no_model_is_told_which_stage_writes_its_chart(self) -> None:
        (self.tree / "docs/event-model/model.yaml").unlink()
        done = self.render()
        self.assertEqual(done.returncode, 0)
        self.assertIn("written by /chart on this profile", done.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
