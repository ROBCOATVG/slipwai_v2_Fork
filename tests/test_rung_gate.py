"""`make check-model` read against the rung the slice's service is on, and the two naming rules.

The gate is a toolkit script that ships inside a generated project, so it is loaded here the way a project
runs it — from `assets/toolkit/scripts/event-model/` — rather than reimplemented. `validate()` takes the
services and the rungs so a suite can state both without writing a `project.json`; in a project both are
read from the manifest, which is where `eventSourced` has lived since it was written.

Three claims. **A model with one slice on each rung passes**, which is the project phase 15 exists to make
generatable. **A field that needs a log is refused by name on a service that keeps none** — a `guard` is a
boundary over a tag query and `folds` is a replay, and a slice naming either on a state-stored service is
describing machinery that service was never given. And **the rung is invisible to the chart**: `chart.py`
reads `context`, `service`, `evt` frames and `reads`, and none of the three fields that move, so the
division of work is the same whichever rung either slice is on.

The naming rules are not rung rules and are tested across both: an event is a named business fact wherever
it is kept.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT

GATE = TOOLKIT_ROOT / "scripts/event-model"


def gate():
    """`check.py`, loaded from the toolkit the way a generated project runs it."""
    sys.path.insert(0, str(GATE))
    try:
        spec = importlib.util.spec_from_file_location("model_gate_check", GATE / "check.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(GATE))


CHECK = gate()
SERVICES = {"orders": ["orders"], "billing": ["billing"]}
#: One service on each rung, which is the mixed project the phase is named for.
MIXED = {"orders": True, "billing": False}


def slice_of(service: str, **over: object) -> dict:
    """A planned state-change slice that passes on either rung, with `over` applied."""
    item: dict = {
        "id": f"S-{service}",
        "pattern": "state-change",
        "status": "planned",
        "capability": "ordering",
        "service": service,
        "context": service,
        "stream": service,
        "actor": "customer",
        "gwt": ["docs/event-model/model.yaml"],
        "code": ["docs/event-model/model.yaml"],
        # One event name per service: two slices producing the same event is its own finding, and this
        # suite is about the rung rather than about that one.
        "frames": [
            {"type": "ui", "name": f"{service.title()}Screen"},
            {"type": "cmd", "name": f"Place{service.title()}"},
            {"type": "evt", "name": f"{service.title()}Placed"},
        ],
    }
    item.update(over)
    return item


def findings(*slices: dict, rungs: dict[str, bool] | None = None) -> list[str]:
    model = {"version": 1, "slices": list(slices)}
    return CHECK.validate(model, SERVICES, MIXED if rungs is None else rungs)


class BothRungsTest(unittest.TestCase):
    def test_one_slice_on_each_rung_passes(self) -> None:
        self.assertEqual(findings(slice_of("orders"), slice_of("billing")), [])

    def test_a_service_the_manifest_says_nothing_about_is_read_as_state_stored(self) -> None:
        """`state` is the `write-model` axis's own `absent`, and a log nobody vouched for is a guess."""
        guarded = slice_of("orders", stream=None, guard={"by": ["seat"], "because": "one seat, one hold"})
        self.assertTrue(any("keeps current state" in line for line in findings(guarded, rungs={})))


class StateStoredTest(unittest.TestCase):
    """The three fields that move, each refused with the reason rather than at a later gate."""

    def refuse(self, **over: object) -> str:
        found = findings(slice_of("billing", **over))
        self.assertTrue(found, "expected a finding")
        return "\n".join(found)

    def test_a_guard_is_refused_and_names_what_to_use_instead(self) -> None:
        said = self.refuse(guard={"by": ["seat"], "because": "one seat, one hold"})
        self.assertIn("needs a log to query", said)
        self.assertIn("`stream`", said)

    def test_folds_are_refused_and_say_why_there_is_nothing_to_replay(self) -> None:
        said = self.refuse(folds=["OrdersPlaced"])
        self.assertIn("nothing to replay", said)
        self.assertIn("saves at the version it read", said)

    def test_a_planned_state_change_still_owes_a_stream(self) -> None:
        said = self.refuse(stream=None)
        self.assertIn("row or aggregate one transaction locks", said)

    def test_a_live_state_view_is_not_asked_for_a_budget_it_cannot_have(self) -> None:
        """`liveBudget` bounds the fold a `live` view does on every query, and there is no fold here."""
        view = {
            "id": "V1", "pattern": "state-view", "status": "planned", "capability": "ordering",
            "service": "billing", "context": "billing", "materialisation": "live",
            "reads": ["OrdersPlaced"], "gwt": ["x"], "code": ["x"],
            "frames": [{"type": "rmo", "name": "Invoices"}],
        }
        self.assertEqual([line for line in findings(slice_of("orders"), view) if "liveBudget" in line], [])


class EventSourcedTest(unittest.TestCase):
    """What the event-sourced rung keeps, so the state rung's rules are a reading and not a rewrite."""

    def test_a_guard_instead_of_a_stream_is_still_the_two_answers_to_one_question(self) -> None:
        guarded = slice_of("orders", stream=None, guard={"by": ["seat"], "because": "one seat, one hold"})
        self.assertEqual(findings(guarded, slice_of("billing")), [])

    def test_folds_are_what_a_decider_rehydrates_from(self) -> None:
        self.assertEqual(findings(slice_of("orders", folds=["OrdersPlaced"]), slice_of("billing")), [])


class NamingTest(unittest.TestCase):
    """Not rung rules: an event is a named business fact on either rung."""

    def named(self, event: str, service: str = "orders", **frame: object) -> str:
        item = slice_of(service, frames=[
            {"type": "ui", "name": "Screen"},
            {"type": "cmd", "name": "DoIt"},
            {"type": "evt", "name": event, **frame},
        ])
        return "\n".join(findings(item))

    def test_a_crud_verb_is_refused_with_the_name_to_use_instead(self) -> None:
        said = self.named("OrdersUpdated")
        self.assertIn("names the write and not the fact", said)
        self.assertIn("`OrdersPlaced`", said)

    def test_the_crud_rule_holds_on_the_state_stored_rung_too(self) -> None:
        self.assertIn("names the write and not the fact", self.named("OrdersUpdated", "billing"))

    def test_an_honestly_crud_event_says_so_and_says_why(self) -> None:
        self.assertEqual(self.named("PageUpdated", crud=True, because="a CMS page is a document"), "")

    def test_the_exemption_without_a_reason_is_the_one_everything_gets(self) -> None:
        self.assertIn("needs a `because`", self.named("PageUpdated", crud=True))

    def test_a_negative_name_is_refused_for_the_failure_underneath_it(self) -> None:
        said = self.named("OrderNotShipped")
        self.assertIn("nothing raises an absence", said)
        self.assertIn("`reason` attribute", said)

    def test_a_name_that_merely_contains_those_letters_is_left_alone(self) -> None:
        """`UserNotified`, `AccountUnlocked` and `ItemUnpacked` are facts, not absences."""
        for name in ("UserNotified", "AccountUnlocked", "ItemUnpacked", "UnitAssigned"):
            with self.subTest(name=name):
                self.assertEqual(self.named(name), "")

    def test_a_business_verb_passes_on_both_rungs(self) -> None:
        for service in ("orders", "billing"):
            with self.subTest(service=service):
                self.assertEqual(self.named("OrderPlaced", service), "")


class ChartTest(unittest.TestCase):
    """The rung is invisible to the division of work, which is what makes it per service at all."""

    def test_the_chart_reads_no_field_the_rung_moves(self) -> None:
        source = (GATE / "chart.py").read_text(encoding="utf-8")
        for field in ("stream", "guard", "folds", "materialisation", "eventSourced", "liveBudget"):
            with self.subTest(field=field):
                self.assertNotIn(f'"{field}"', source)
                self.assertNotIn(f"'{field}'", source)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
