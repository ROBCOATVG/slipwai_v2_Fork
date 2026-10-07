"""One file per event, and an index nobody writes.

Two slices in one context both add an event. In version 1 both edited `events.py`, both added a class at
the end, and the merge was a conflict in the same three lines — every time, for every pair, in a file that
only ever grows. The resolution is always "take both", which is the definition of a conflict that should
not have been one.

So an event is a file named after its mark, and the index that imports them is generated. The merge of two
additions is two new files and a regeneration, which git does without asking anybody anything.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.project import events_index as events

PY_PATH = "service/src/ordering/domain/<context>/events.py"
TS_PATH = "apps/web/src/domain/events.ts"
GO_PATH = "internal/ordering/domain/events.go"


class LayoutTest(unittest.TestCase):
    def test_a_module_becomes_a_directory_without_a_second_protocol_answer(self) -> None:
        self.assertEqual(events.events_directory(PY_PATH), "service/src/ordering/domain/<context>/events")

    def test_a_backend_already_naming_a_directory_is_left_alone(self) -> None:
        self.assertEqual(events.events_directory("src/domain/events"), "src/domain/events")

    def test_an_event_file_is_named_after_its_mark(self) -> None:
        """So the chart, the log line and the file all say one word, and grepping the mark finds the file."""
        self.assertEqual(events.event_file(PY_PATH, "OrderPlaced"),
                         "service/src/ordering/domain/<context>/events/OrderPlaced.py")

    def test_two_events_are_two_files_and_share_no_path(self) -> None:
        one = events.event_file(PY_PATH, "OrderPlaced")
        two = events.event_file(PY_PATH, "OrderCancelled")
        self.assertNotEqual(one, two)


class IndexTest(unittest.TestCase):
    def test_python_re_exports_each_file(self) -> None:
        written = events.index(PY_PATH, ["OrderPlaced", "OrderCancelled"])
        assert written is not None
        self.assertIn("from .OrderPlaced import *", written)
        self.assertIn("from .OrderCancelled import *", written)

    def test_typescript_re_exports_each_file(self) -> None:
        written = events.index(TS_PATH, ["OrderPlaced"])
        assert written is not None
        self.assertIn('export * from "./OrderPlaced";', written)

    def test_a_language_whose_directory_is_already_a_namespace_gets_none(self) -> None:
        """Go needs no index, and generating an empty one would be a file to keep in step for nothing."""
        self.assertIsNone(events.index(GO_PATH, ["OrderPlaced"]))
        self.assertIsNone(events.index_path(GO_PATH))

    def test_the_index_is_sorted_so_merge_order_cannot_change_it(self) -> None:
        """Which is the whole point: the merge of two additions is a regeneration, not a resolution."""
        one = events.index(PY_PATH, ["OrderPlaced", "OrderCancelled"])
        two = events.index(PY_PATH, ["OrderCancelled", "OrderPlaced"])
        self.assertEqual(one, two)

    def test_the_index_says_it_is_generated_and_why_editing_it_is_refused(self) -> None:
        written = events.index(PY_PATH, ["OrderPlaced"])
        assert written is not None
        self.assertIn("Never edit", written)
        self.assertIn("one file per event exists to remove", written)

    def test_the_index_goes_beside_the_events_it_imports(self) -> None:
        self.assertEqual(events.index_path(PY_PATH),
                         "service/src/ordering/domain/<context>/events/__init__.py")


class MergeTest(unittest.TestCase):
    """The claim the slice is for, written as the thing it claims."""

    def test_two_slices_each_adding_an_event_touch_no_shared_line(self) -> None:
        base = ["OrderPlaced"]
        one = events.event_file(PY_PATH, "OrderCancelled")
        two = events.event_file(PY_PATH, "OrderRefunded")
        self.assertNotEqual(one, two)
        # The only file both change is the index, and the index is rendered rather than merged.
        after_one = events.index(PY_PATH, [*base, "OrderCancelled"])
        after_two = events.index(PY_PATH, [*base, "OrderRefunded"])
        both = events.index(PY_PATH, [*base, "OrderCancelled", "OrderRefunded"])
        self.assertNotEqual(after_one, after_two)
        assert both is not None and after_one is not None and after_two is not None
        for line in after_one.splitlines() + after_two.splitlines():
            with self.subTest(line=line):
                self.assertIn(line, both, "a regeneration takes both sides, which is why it is not a merge")


class ChartTest(unittest.TestCase):
    def test_the_events_come_from_the_chart_because_both_profiles_have_one(self) -> None:
        chart = {"marks": {"OrderPlaced": {"kind": "event"}, "POST /orders": {"kind": "route"},
                           "PricingPort": {"kind": "port"}, "InvoiceRaised": {"kind": "event"}}}
        self.assertEqual(events.event_marks(chart), ["InvoiceRaised", "OrderPlaced"])

    def test_a_chart_with_no_marks_block_yields_none(self) -> None:
        self.assertEqual(events.event_marks({}), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
