"""slipwai's own mark: a little tug whose funnel puffs a spark.

A tug is the boat that moves the big one, which is the whole of what this does — a project is the ship and
this is the thing that gets it off the slipway. It is drawn cute on purpose: the terminal is already stern
enough, and a dashboard somebody keeps open all day is better for having something friendly in the corner.

The spark is the only place the mark says anything about what runs it, and it is a *substitution* rather
than an addition: the puff a funnel makes is a spark instead of coal. A circuit board or a hexagon would
have said the same thing in the same way everybody else says it.

**One colour first.** `MONO` knocks the porthole and the funnel's band out rather than painting them, so
the mark holds as a favicon, on a stamp, and anywhere `currentColor` is all there is. `COLOUR` is the same
drawing with the palette's teal and brass in it, for a README or a page that wants it.

Read from `assets/brand/` rather than written here, because an SVG in a Python string is an SVG nobody
opens in anything that can draw it.
"""
from __future__ import annotations

import base64
from functools import lru_cache

from .assets import ROOT

BRAND = ROOT / "assets/brand"
MARK = "slipwai-mark.svg"
MONO = "slipwai-mark-mono.svg"


@lru_cache(maxsize=4)
def svg(name: str = MONO) -> str:
    """One of the marks, as it is on disk. The XML declaration and the title come with it."""
    return (BRAND / name).read_text(encoding="utf-8").strip()


def inline(name: str = MONO, css_class: str = "mark", title: str = "slipwai") -> str:
    """The mark, ready to drop into a page: a class to style it by, and a title a screen reader reads.

    Inlined rather than linked, because the pages this goes on are self-contained — the bridge's published
    copy is one file, and a `<img src>` would be the one thing on it that 404s.
    """
    found = svg(name).replace("<svg ", f'<svg class="{css_class}" ', 1)
    return found.replace("<title>slipwai</title>", f"<title>{title}</title>")


def favicon(colour: str = "#0f6b6b") -> str:
    """The mark as a `data:` URI for a `<link rel="icon">`, in one colour.

    A data URI rather than a file for the same reason: a published page is one file, and a favicon that
    only resolved on the served copy would be a tab icon that works in half the places the page opens.
    """
    found = svg(MONO).replace("currentColor", colour)
    encoded = base64.b64encode(found.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
