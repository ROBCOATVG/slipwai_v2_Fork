"""Where the product is, and how dark a merge is because of it.

In version 1 the `release` setting was `flagged` or `park`, and `flagged` was absolute: every slice opened
or continued a flag seeded off, `check-flags` demanded the key be declared, read and tested on two paths,
and a slice with nothing holding it back parked for a person. On a product in service that is exactly right,
because merging and releasing are two decisions. On a product on the slipway, with no production and no
actor but the team, it is pure drag — a reader to call, two test paths, a key to hoist before every demo —
and MANDA ran five berths under it on a product nobody used yet.

The fix is not a knob. **It is one fact about the product, recorded once, that the mode follows from.** A
setting a person turns is a setting that is wrong whenever somebody forgets to turn it; a fact about where
the product is gets corrected because it is visibly untrue.

    slipway      no production, or one only the team sees   → open
    sea trials   a production with known pilot actors       → keystone
    in service   real actors use what trunk deploys         → flagged

`promoted` is the fourth mode and is not derived, because it is a fact about how a team deploys rather than
about where the product is: production takes a promoted build rather than every push. A project says so and
keeps saying so.

**The state is a product decision and the mode follows from it, never the other way round.** A person moves
a product from slipway to sea trials when its first pilot actor appears, and to in service when it has
actors it cannot surprise. Both are written with an ADR, because both change what a merge means, and
`/cruise` never changes either.
"""
from __future__ import annotations

#: Where a product is, in the order it moves. The field is `state` in `project.json`.
STATES = ("slipway", "sea-trials", "in-service")
DEFAULT_STATE = "slipway"
#: How dark a merge is. Theme E defines each.
MODES = ("open", "keystone", "flagged", "promoted")
#: Which mode a state implies. `promoted` is nobody's default: it is a fact about deployment, not about the
#: product, so a project that wants it says so and keeps saying so.
MODE_OF_STATE = {"slipway": "open", "sea-trials": "keystone", "in-service": "flagged"}

WHAT_A_MERGE_MEANS = {
    "open": "visible at once — trunk is the demo",
    "keystone": "dark by omission — every slice lands except the entry point, which is the capability's "
                "last slice's last task",
    "flagged": "dark behind a key seeded off, which only a person hoists",
    "promoted": "visible on trunk and in preview; production takes only what passes the promotion gate",
}


def release_mode(state: str, declared: str | None = None) -> str:
    """The mode this product merges under.

    A project may declare `promoted` and keep it, because that is a fact about how it deploys that no
    product state implies. Anything else declared is ignored in favour of the state: a mode that disagreed
    with where the product is would be the version 1 setting back again, wrong the moment somebody forgot
    to turn it.
    """
    if declared == "promoted":
        return "promoted"
    return MODE_OF_STATE.get(state, MODE_OF_STATE[DEFAULT_STATE])


def flags_wanted(state: str, declared: str | None = None) -> bool:
    """Whether this product generates a flag reader at all.

    A slipway product does not, and that is most of what this slice buys: no reader to call, no second test
    path, no key to hoist before a demo, and no park for a slice with nothing holding it back.
    """
    return release_mode(state, declared) == "flagged"


def release_section(state: str, declared: str | None = None) -> str:
    """The `/drive` section its merge rung reads to know how dark this merge is."""
    mode = release_mode(state, declared)
    others = "\n".join(f"- **{name}** — {WHAT_A_MERGE_MEANS[name]}" for name in MODES if name != mode)
    return f"""### How dark a merge is here

This product's state is **{state}**, recorded in `project.json`, and its release mode follows from it:
**{mode}**. A merge is {WHAT_A_MERGE_MEANS[mode]}.

The mode is not a setting to weigh per slice. It is read, once, at the merge rung, and the slice merges that
way. Version 1 asked the question of every slice and the answer was the same every time, which is a stop
that costs a stage and decides nothing.

The other three, so a reader knows what moving the product would change:

{others}

**Moving the product is a person's decision and an ADR**, because it changes what every later merge means:
to `sea-trials` when the first pilot actor appears, to `in-service` when there are actors it cannot
surprise. A run never changes it. `promoted` is the one mode no state implies — it says production takes a
promoted build rather than every push, which is a fact about how this team deploys — so a project that
wants it declares it and keeps it.
"""
