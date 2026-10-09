"""What the backend protocol owes the rung, and what it owes a language that has not caught up yet.

15.2 made the keel give each service the files its write model names, and 15.5 made the pages say it. This
is the half the languages answer: a backend declares what a state-stored service is given, where that
service's repository port lands, and under a member whose name no longer says `event store` — because the
store on this rung holds current state and calling the answer `event_store_directory` sends a reader of the
generated prose looking for a log.

Two kinds of failure are guarded. The first is a silent one: a backend that answers nothing for the rung
generates a service with no persistence at all, because core skips a feature the layout lacks — so the
project is written, the gate is green, and the hole is found by whoever opens the directory. That has to be
a finding of `slipwai package check` (`rung_findings`), and the suite has to actually generate on the rung,
because a declaration that names an asset the package never committed is not a declaration anybody can act
on. The second is the opposite risk, and it is the one a rename creates: every language is a repository of
its own, and a keel that renames a member and refuses the old name in the same release breaks every package
on the day it ships. Hence the window — both names read, the new one first — and hence a test for each
direction of it, because a window nobody proved is a window that closed early.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import checkout_packages
from registry_fakes import fake_language, family_answers, required_answers

from slipwai.conformance.generation import asked, rung_findings, runs
from slipwai.project.event_model import code_paths, event_documentation
from slipwai.registry import (
    EVENT_MODEL_PATHS,
    EVENT_STORE_DIRECTORY,
    PERSISTENCE_DIRECTORY,
    WRITE_SIDE_FILES,
    Backend,
    Family,
    Language,
    Member,
    Registry,
    RegistryError,
    load,
    registry,
)
from slipwai.rungs import STATE, WRITE_MODEL
from slipwai.selection import Selection
from slipwai.services import service_app

TOY = "toy-plain"
EVENT_SOURCED = Selection({"write-model": "events", "persistence": "postgres"})
STATE_STORED = Selection({"write-model": "state", "persistence": "postgres"})


def directory(path: str) -> str:
    """A `persistence_directory` answer, under either name: where one service's driven adapters land."""
    return f"{path}/adapters/"


def other(path: str) -> str:
    """A second answer, told apart from the first by what it returns and by nothing else."""
    return f"{path}/persistence/"


class RenamedMemberTest(unittest.TestCase):
    """`event_store_directory` became `persistence_directory`, and both are read until 2.1."""

    def test_a_backend_that_answers_only_the_old_name_still_loads(self) -> None:
        """A language released before the rename is a language that still works (`docs/backend-protocol.md`,
        *Renamed members*)."""
        answers = required_answers(without=(PERSISTENCE_DIRECTORY,), extra={EVENT_STORE_DIRECTORY: directory})
        loaded = load([fake_language("old", answers=answers)])
        self.assertEqual("apps/orders/adapters/", loaded.answer("old", PERSISTENCE_DIRECTORY)("apps/orders"))

    def test_a_backend_that_answers_neither_is_missing_the_name_it_should_answer(self) -> None:
        """The refusal names the member a language is asked for today, never the one it is being let off."""
        with self.assertRaises(RegistryError) as raised:
            load([fake_language("neither", answers=required_answers(without=(PERSISTENCE_DIRECTORY,)))])
        self.assertIn("backend neither is missing persistence_directory", str(raised.exception))
        self.assertNotIn("event_store_directory", str(raised.exception))

    def test_a_backend_that_has_moved_is_read_by_the_name_it_moved_to(self) -> None:
        """A package part-way through the window answers both; the new name is the one it means."""
        answers = required_answers(extra={PERSISTENCE_DIRECTORY: other, EVENT_STORE_DIRECTORY: directory})
        loaded = load([fake_language("both", answers=answers)])
        self.assertEqual("apps/orders/persistence/", loaded.answer("both", PERSISTENCE_DIRECTORY)("apps/orders"))

    def test_a_backend_that_has_moved_beats_a_family_that_has_not(self) -> None:
        """Across names the new one wins, and across holders the backend's own does: a framework that has
        caught up is not pulled back by the family it belongs to."""
        language = Language(
            (Family("slow", {**family_answers(), EVENT_STORE_DIRECTORY: directory}),),
            (Backend("slow-fast", "slow", required_answers(without=(PERSISTENCE_DIRECTORY,))
                     | {PERSISTENCE_DIRECTORY: other}),),
        )
        self.assertEqual("apps/o/persistence/", load([language]).answer("slow-fast", PERSISTENCE_DIRECTORY)("apps/o"))

    def test_the_old_name_is_still_declared_so_answering_it_is_not_a_fault(self) -> None:
        """A deprecated member deleted from `PROTOCOL` would be refused as a key the protocol never had,
        which is a worse line to hand a language author than the one asking them to rename."""
        self.assertFalse(EVENT_STORE_DIRECTORY.required)
        self.assertIs(PERSISTENCE_DIRECTORY.was, EVENT_STORE_DIRECTORY)
        self.assertIsNone(EVENT_STORE_DIRECTORY.was)


@unittest.skipUnless(checkout_packages.installed("toy"), "the toy package is not checked out")
class RepositoryPathTest(unittest.TestCase):
    """`event_model_paths` gained `repository`, which only the state-stored page reads.

    The backend is the toy by key and a fake by answers: the key has to be one the catalogue knows, because
    a service names its family and framework through it, and the answer has to be this test's, because what
    is under test is what core does with a language that answers four keys and one that answers five.
    """

    def paths(self, answer: object) -> dict[str, str]:
        language = fake_language(TOY, answers=required_answers(extra={EVENT_MODEL_PATHS: answer}))
        service = service_app("billing", TOY, 3000, STATE_STORED, first=True)
        with mock.patch("slipwai.project.event_model.registry", lambda: load([language])):
            return code_paths("shop", service)

    def test_a_backend_that_answers_the_key_is_read_as_it_wrote_it(self) -> None:
        def answered(project: str, service: str) -> dict[str, str]:
            return {"events": "e", "domain": "d", "usecase": "u", "test": "t",
                    "repository": f"{service}/application/repository.ts"}

        self.assertEqual("apps/billing/application/repository.ts", self.paths(answered)["repository"])

    def test_a_backend_written_before_the_rung_gets_the_path_of_the_decision_it_belongs_to(self) -> None:
        """For one MINOR: a page about where code goes shows the port with the decision rather than
        leaving the row blank, and `slipwai package check` is what asks the language to answer it."""
        def four(project: str, service: str) -> dict[str, str]:
            return {"events": "e", "domain": f"{service}/domain/decide.ts", "usecase": "u", "test": "t"}

        self.assertEqual("apps/billing/domain/decide.ts", self.paths(four)["repository"])


@unittest.skipUnless(checkout_packages.installed("toy"), "the toy package is not checked out")
class ConformanceRungTest(unittest.TestCase):
    """What `slipwai package check` asks of a backend about the rung, run against the one package here."""

    def test_the_toy_owes_the_state_stored_rung_nothing(self) -> None:
        self.assertEqual([], rung_findings(registry(), TOY))

    def test_a_backend_with_no_state_rows_is_named_per_store_it_offers(self) -> None:
        """The finding a generated page with a hole in it would otherwise be (plan 15.6)."""
        loaded = registry()
        rows = {feature: files for feature, files in loaded.answer(TOY, WRITE_SIDE_FILES).items()
                if feature != STATE}
        found = rung_findings(self.without(loaded, {WRITE_SIDE_FILES: rows}), TOY)
        self.assertIn("backend toy-plain offers persistence postgres, and write_side_files answers nothing for "
                      "it on the state rung: a service answered write-model state would get no store", found)

    def test_a_backend_that_answers_no_repository_path_is_named(self) -> None:
        def four(project: str, service: str) -> dict[str, str]:
            return {"events": "e", "domain": "d", "usecase": "u", "test": "t"}

        found = rung_findings(self.without(registry(), {EVENT_MODEL_PATHS: four}), TOY)
        self.assertIn("backend toy-plain answers event_model_paths with no repository, which the page that says "
                      "where a slice's code lands reads", found)

    def without(self, loaded: Registry, replaced: dict[Member[Any], object]) -> Registry:
        """`loaded` with the toy's answers overridden, as a language that has not answered them would be."""
        backend = loaded.backends[TOY]
        swapped = Backend(backend.key, backend.family, {**backend.answers, **replaced})
        return Registry(loaded.families, {**loaded.backends, TOY: swapped}, loaded.roots)

    def test_the_suite_generates_the_rung_rather_than_only_reading_what_it_declares(self) -> None:
        """A `state` block naming an asset the package never committed generates nothing, and no reading of
        the declaration finds that out."""
        with tempfile.TemporaryDirectory(prefix="slipwai-rung-") as output:
            done = runs(Path(output), TOY)
            state = [run for run in done if (WRITE_MODEL, STATE) in run.choices]
            self.assertEqual(1, len(state), [run.choices for run in done])
            self.assertEqual("event-modelling at write-model state", asked(state[0]))
            self.assertIsNotNone(state[0].project, state[0].said)
            service = state[0].project / "apps/service"  # type: ignore[operator]
            self.assertTrue((service / "adapters/repository_postgres.txt").is_file(),
                            sorted(p.name for p in service.rglob("*")))
            self.assertFalse((service / "adapters/event_store_postgres.txt").exists())


@unittest.skipUnless(checkout_packages.installed("toy"), "the toy package is not checked out")
class FirstSliceTreeTest(unittest.TestCase):
    """`docs/first-slice.md`, whose tree is the list of files somebody is about to open."""

    def tree(self, selection: Selection) -> str:
        service = service_app("billing", TOY, 3000, selection, first=True)
        return event_documentation("shop", [service])["docs/first-slice.md"]

    def test_a_state_stored_service_is_shown_the_port_it_loads_and_saves_through(self) -> None:
        self.assertIn("application/<context>/repository.txt   the port current state is loaded and saved through",
                      self.tree(STATE_STORED))

    def test_an_event_sourced_service_is_shown_no_such_file(self) -> None:
        """Its write side is the event-store port, named in the write-model table; a line here would be a
        file the reader is told to open and will not find."""
        self.assertNotIn("repository.txt", self.tree(EVENT_SOURCED))
