"""The mark: a little tug whose funnel puffs a spark.

A logo is a thing nobody tests and everybody breaks. What is held here is the handful of properties that
make it usable rather than the drawing itself: one colour works, it is inlined rather than linked, nothing
in it depends on a file the published copy will not have, and the id it carries cannot collide with itself.
"""
from __future__ import annotations

import re
import unittest

import checkout_packages  # noqa: F401

from slipwai.brand import BRAND, MARK, MONO, favicon, inline, svg


class FileTest(unittest.TestCase):
    def test_both_marks_are_on_disk_and_are_svg(self) -> None:
        """Read from a file rather than a Python string: an SVG in a string is one nobody opens in
        anything that can draw it."""
        for name in (MARK, MONO):
            with self.subTest(name=name):
                self.assertTrue((BRAND / name).is_file())
                self.assertTrue(svg(name).startswith("<svg"))

    def test_each_names_itself_for_a_screen_reader(self) -> None:
        for name in (MARK, MONO):
            with self.subTest(name=name):
                self.assertIn('role="img"', svg(name))
                self.assertIn("<title>slipwai</title>", svg(name))

    def test_the_mono_mark_is_one_colour_and_knocks_out_the_rest(self) -> None:
        """A good logo works in a single colour first. The porthole and the funnel's band are holes."""
        found = svg(MONO)
        self.assertNotIn("#0f6b6b", found)
        self.assertNotIn("#8a6d24", found)
        self.assertIn("mask", found)

    def test_it_scales_because_it_declares_no_size(self) -> None:
        for name in (MARK, MONO):
            with self.subTest(name=name):
                self.assertNotRegex(svg(name), r"<svg[^>]*\swidth=")
                self.assertIn('viewBox="0 0 32 32"', svg(name))

    def test_nothing_in_it_is_a_raster_effect(self) -> None:
        """Filters, blurs and shadows do not scale cleanly and are most of an SVG's weight."""
        for name in (MARK, MONO):
            for banned in ("<filter", "feGaussianBlur", "drop-shadow", "<image"):
                with self.subTest(name=name, banned=banned):
                    self.assertNotIn(banned, svg(name))

    def test_it_is_small_enough_to_inline_twice_without_thinking_about_it(self) -> None:
        for name in (MARK, MONO):
            with self.subTest(name=name):
                self.assertLess(len(svg(name)), 3000)


class InlineTest(unittest.TestCase):
    def test_it_carries_a_class_to_style_it_by(self) -> None:
        self.assertIn('<svg class="mark"', inline())

    def test_the_spark_is_its_own_group_so_a_page_can_give_it_a_colour(self) -> None:
        """The hull follows the theme; the spark gets the brass. Neither is fixed in the file."""
        self.assertIn('class="spark"', inline())

    def test_a_title_can_be_given_for_the_page_it_sits_on(self) -> None:
        self.assertIn("<title>the little tug</title>", inline(title="the little tug"))

    def test_the_mask_id_is_distinctive_because_it_gets_inlined_more_than_once(self) -> None:
        found = re.findall(r'id="([^"]+)"', inline())
        self.assertTrue(found)
        for one in found:
            with self.subTest(id=one):
                self.assertGreater(len(one), 10, "a short id collides with whatever else is on the page")


class FaviconTest(unittest.TestCase):
    def test_it_is_a_data_uri_so_a_published_page_keeps_its_icon(self) -> None:
        """A published bridge is one file; a linked favicon is the one thing on it that would 404."""
        self.assertTrue(favicon().startswith("data:image/svg+xml;base64,"))

    def test_it_is_painted_because_currentColor_means_nothing_in_a_tab(self) -> None:
        import base64
        body = base64.b64decode(favicon("#0f6b6b").split(",", 1)[1]).decode("utf-8")
        self.assertIn("#0f6b6b", body)
        self.assertNotIn("currentColor", body)


class OnThePageTest(unittest.TestCase):
    def test_the_bridge_carries_it_top_right_and_as_its_icon(self) -> None:
        from slipwai.bridge_page import page
        found = {"berths": [], "inbox": [], "streams": {}, "feed": [], "unreadable": {},
                 "pressure": {"position": "half-ahead", "boilers": 3, "fanout": 2,
                              "bunker_per_day": 10000, "banked": ""},
                 "bunker": {"spent": None, "allowed": 10000}}
        said = page(found, {})
        self.assertIn('class="mark"', said)
        self.assertIn('rel="icon"', said)
        self.assertIn("justify-content:space-between", said)

    def test_it_follows_the_theme_rather_than_carrying_two_fixed_colours(self) -> None:
        """A mark with the light palette baked in is a mark that is wrong on half the pages it opens on."""
        from slipwai.bridge_page import STYLE
        self.assertIn(".mark{", STYLE.replace(" ", ""))
        self.assertIn("var(--teal)", STYLE)
        self.assertIn("var(--brass)", STYLE)


if __name__ == "__main__":
    unittest.main()


class ThemeTest(unittest.TestCase):
    """Auto, Light and Dark. Three states because two can only mean "the system's, or the other one"."""

    def page(self, controls: bool = True) -> str:
        from slipwai.bridge_page import page
        found = {"berths": [], "inbox": [], "streams": {}, "feed": [], "unreadable": {},
                 "pressure": {"position": "half-ahead", "boilers": 3, "fanout": 2,
                              "bunker_per_day": 10000, "banked": ""},
                 "bunker": {"spent": None, "allowed": 10000}}
        return page(found, {}, controls=controls)

    def test_it_offers_all_three(self) -> None:
        said = self.page()
        for one in ("t-auto", "t-light", "t-dark"):
            with self.subTest(state=one):
                self.assertIn(one, said)

    def test_auto_is_the_one_that_starts_checked(self) -> None:
        """Following the system is the only default that is nobody's opinion."""
        self.assertIn('id="t-auto" checked', self.page())

    def test_each_state_sets_the_tokens_rather_than_only_turning_one_off(self) -> None:
        """Light has to override the dark media query, so it cannot be "the absence of dark"."""
        from slipwai.bridge_page import STYLE
        for rule in (":root:has(#t-dark:checked)", ":root:has(#t-light:checked)",
                     ":root:has(#t-auto:checked)"):
            with self.subTest(rule=rule):
                self.assertIn(rule, STYLE)

    def test_it_works_with_no_script_at_all(self) -> None:
        """Which is what the published copy has: radios and `:has()`, never a listener."""
        said = self.page(controls=False)
        self.assertIn("t-dark", said)
        self.assertNotIn("<script>", said)

    def test_the_script_only_remembers_the_choice(self) -> None:
        """The page reloads after every control; a theme that reset each time is one nobody sets."""
        from slipwai.bridge_page import SCRIPT
        self.assertIn("localStorage", SCRIPT)
        self.assertIn("slipwai-bridge-theme", SCRIPT)
