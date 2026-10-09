"""The rung a service is on, and which half of a backend's declaration it reads.

A service's *write model* is how it decides and records a write: `events`, where the log is the truth and
state is a fold of it, or `state`, where the service keeps current state and the events the model names are
contracts raised after the write and never replayed. Rung 4 and rung 2 of the constitution's own ladder.
`catalog.json` asks it per service on the `write-model` axis; the names are here, below the selection, so
that the loader and the protocol can speak of a rung without knowing what a selection is.

What a rung settles is *what the store is asked to hold*, not which store it is — the persistence axis has
already chosen that. So a backend declares both sets against the same feature keys: its feature rows at the
top, which are what an event-sourced service is given, and the state-stored rung's rows under one `state`
key beside them. One member per side and not two, because it is one question asked once per rung: what does
this store answer with.

A backend that declares no `state` block answers a state-stored service with nothing. That is the honest
shape of a language that has not written the skeleton yet — `slipwai package check` names it (plan 15.6) —
rather than a generated page with a hole in it.
"""
from __future__ import annotations

#: The axis that carries the rung, and its two answers. `state` is the axis's `absent`, so a service on a
#: profile that was never asked reads `state`, which is what a service with no model is.
WRITE_MODEL = "write-model"
EVENTS, STATE = "events", "state"

#: Feature → where the file lands under the service → the asset it is copied from.
Layout = dict[str, dict[str, str]]


def merged_layout(write_side: Layout, read_side: Layout) -> Layout:
    """The write side's layout with the read side folded into it, feature by feature, in the write side's order.

    A feature lands because the write side lands it; the read side only adds files to it. The keys cannot
    collide: a path names one file, and each side ships its own.
    """
    return {feature: {**files, **read_side.get(feature, {})} for feature, files in write_side.items()}


def rung_rows(declared: dict, write_model: str) -> Layout:
    """The feature rows one rung reads, out of what one side declares for both."""
    rows = (declared.get(STATE) or {}) if write_model == STATE else declared
    return {feature: dict(files) for feature, files in rows.items() if feature != STATE}


def every_rung(declared: dict) -> Layout:
    """Every file one side declares on either rung, feature by feature.

    What a check about a *feature* asks, rather than about a service: a prune row is written per feature and
    has to cover the files of both rungs, and the loader's check that a declared asset is a file in the
    package's own directory is about every asset the package names, whoever is given it.
    """
    found: Layout = {}
    for rung in (EVENTS, STATE):
        for feature, files in rung_rows(declared, rung).items():
            found.setdefault(feature, {}).update(files)
    return found
