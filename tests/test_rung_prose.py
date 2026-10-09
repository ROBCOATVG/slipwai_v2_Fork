"""The pages a generated project reads, held to the rung each of its services is actually on.

15.2 made the keel *give* each service the files its write model names. This suite is about what the pages
then *say*, which is the half a person and an agent act on: a service handed a repository and a state table
is no better off if `AGENTS.md` tells whoever works in it to fold a log, and `docs/event-modeling-to-code.md`
showing one table for the project hands the first service's rung silently to every other one.

Three failures are guarded here. A mixed project describing only one of its rungs — the one the first
service happens to be on — is the first, and it is the one that would go unnoticed longest, because every
page would still be internally consistent. A state-stored project told to append to a stream is the second:
the prose would be describing a port that service was never given. And a state-stored project whose
concurrency paragraph claims a `(stream_id, version)` race is the third, which is worse than wrong — it
names a test somebody could believe they had written.

The generation half runs against the toy package, because the paths in the mapping document come from a
backend answering `EVENT_MODEL_PATHS` and a fake would prove only that a dictionary was read.
"""
from __future__ import annotations

import unittest

import checkout_packages

from slipwai.project.adversary import adversary_command
from slipwai.project.commands import constitution_coverage_command, gaps_command
from slipwai.project.docs import documentation_files
from slipwai.project.guidance import agent_guidance, architecture
from slipwai.project.ladder import drive_ladder
from slipwai.project.readme import readme
from slipwai.project.repository import pull_request_template
from slipwai.selection import Selection
from slipwai.services import App, service_app

TOY = "toy-plain"
EVENT_SOURCED = Selection({"write-model": "events", "persistence": "postgres"})
STATE_STORED = Selection({"write-model": "state", "persistence": "postgres"})

# What a page on the event-sourced rung is allowed to say and a state-stored one is not. Each is a claim
# about machinery — a log to replay, a stream to append to, a port that does both — rather than a word that
# happens to appear: `stream` on its own is a field both rungs carry, and `replay` is also the name of one
# of the factory's own verbs, so neither is searched for bare.
LOG_CLAIMS = (
    "the event store is a driven port",
    "event-store port",
    "appends with an expected version",
    "a Decider:",
    "folds the stream into state",
    "catch-up subscription",
    "`(stream_id, version)` unique constraint",
)


def mixed() -> list[App]:
    """One service on each rung, which is the project phase 15 exists to make generatable."""
    return [
        service_app("orders", TOY, 3000, EVENT_SOURCED, first=True),
        service_app("billing", TOY, 3001, STATE_STORED),
    ]


def state_only() -> list[App]:
    return [service_app("billing", TOY, 3000, STATE_STORED, first=True)]


def sourced_only() -> list[App]:
    return [service_app("orders", TOY, 3000, EVENT_SOURCED, first=True)]


class PagesTest(unittest.TestCase):
    """The pages that take the services directly and need no language package to render."""

    def pages(self, apps: list[App]) -> dict[str, str]:
        return {
            "docs/architecture.md": architecture("event-modelling", apps),
            "AGENTS.md": agent_guidance("event-modelling", apps),
            "README.md": readme("shop", "event-modelling", apps),
            "commands/adversary.md": adversary_command(True, apps),
            "commands/gaps.md": gaps_command(True, apps),
            "commands/constitution-coverage.md": constitution_coverage_command(True, apps),
            ".github/PULL_REQUEST_TEMPLATE.md": pull_request_template("event-modelling", apps, "none"),
            "commands/drive.md": drive_ladder(True, apps, "none"),
        }

    def test_a_state_stored_project_claims_no_log_anywhere(self) -> None:
        """The claim each page would otherwise carry is a port the service was never given (15.2)."""
        for name, page in self.pages(state_only()).items():
            for claim in LOG_CLAIMS:
                with self.subTest(page=name, claim=claim):
                    self.assertNotIn(claim.lower(), page.lower())

    def test_an_event_sourced_project_still_reads_as_it_did(self) -> None:
        """The default path is unchanged by phase 15, and these are the sentences that say so."""
        pages = self.pages(sourced_only())
        self.assertIn("The event store is a driven port", pages["AGENTS.md"])
        self.assertIn("stream identity", pages["docs/architecture.md"])
        self.assertIn("event-sourcing obligations", pages["commands/constitution-coverage.md"])

    def test_a_mixed_project_names_both_rungs_and_which_service_is_on_each(self) -> None:
        """A page that describes two rungs without saying which service is which has said nothing."""
        pages = self.pages(mixed())
        for name in ("docs/architecture.md", "AGENTS.md", "README.md"):
            with self.subTest(page=name):
                self.assertIn("`apps/orders`", pages[name])
                self.assertIn("`apps/billing`", pages[name])
                self.assertIn("current state", pages[name])

    def test_the_concurrency_paragraph_names_the_race_this_store_can_actually_lose(self) -> None:
        """A state service's Postgres has no `(stream_id, version)` constraint to race on, so a test
        written against that sentence would assert a guarantee nobody implemented."""
        self.assertIn("version the state was read at", agent_guidance("event-modelling", state_only()))
        self.assertIn("`(stream_id, version)`", agent_guidance("event-modelling", sourced_only()))

    def test_the_adversary_trigger_table_only_offers_rows_a_slice_here_can_answer(self) -> None:
        """A row every slice marks `not present` teaches the reader to skim the table it is in."""
        self.assertNotIn("stream identity", adversary_command(True, state_only()))
        self.assertIn("the version a state-stored write is saved at", adversary_command(True, state_only()))
        self.assertIn("stream identity", adversary_command(True, sourced_only()))

    def test_the_model_rung_says_what_naming_the_service_settles_only_where_it_settles_something(self) -> None:
        """With both rungs present the service decides which fields the slice may carry; with one rung it
        decides nothing, and the longest rung on the ladder does not grow a paragraph about it."""
        self.assertIn("`guard` and\n   `folds` are refused", drive_ladder(True, mixed(), "none"))
        self.assertNotIn("are refused", drive_ladder(True, sourced_only(), "none"))

    def test_the_pull_request_asks_about_the_rung_only_in_a_project_that_has_two(self) -> None:
        for apps, expected in ((mixed(), True), (sourced_only(), False), (state_only(), False)):
            with self.subTest(services=[app.name for app in apps]):
                template = pull_request_template("event-modelling", apps, "none")
                self.assertEqual("raised the way its service's rung says" in template, expected)


@unittest.skipUnless(checkout_packages.installed("toy"), "the toy package is not checked out")
class MappingDocumentTest(unittest.TestCase):
    """`docs/event-modeling-to-code.md`, which is the page a slice is written against."""

    def document(self, apps: list[App]) -> str:
        return documentation_files("shop", "event-modelling", apps)["docs/event-modeling-to-code.md"]

    def test_a_mixed_project_carries_a_table_per_service(self) -> None:
        """One table would describe the first service's rung and hand it silently to the second."""
        written = self.document(mixed())
        self.assertIn("## `apps/orders` — the log is the truth", written)
        self.assertIn("## `apps/billing` — current state is the truth", written)
        self.assertEqual(written.count("| Model element | Code responsibility | Initial location |"), 2)

    def test_the_state_stored_table_says_repository_where_the_other_says_decider(self) -> None:
        self.assertIn("a Decider:", self.document(sourced_only()))
        self.assertIn("a load through the repository port", self.document(state_only()))
        self.assertNotIn("a Decider:", self.document(state_only()))

    def test_the_state_stored_table_refuses_the_two_fields_that_need_a_log_by_name(self) -> None:
        """`guard` and `folds` are on every slice the modelling skill teaches, so the table has to say
        they are refused here — a field left out reads as one nobody thought about (15.4 is the gate)."""
        written = self.document(state_only())
        self.assertIn("| `guard` | refused on this rung by name", written)
        self.assertIn("| `folds` | refused for the same reason", written)

    def test_a_live_read_model_is_asked_for_a_budget_only_where_there_is_a_log_to_bound(self) -> None:
        self.assertIn("asks no `liveBudget` on this rung", self.document(state_only()))
        self.assertIn("A `live` view names `liveBudget` too", self.document(sourced_only()))

    def test_every_service_gets_its_own_paths_and_its_own_test_line(self) -> None:
        written = self.document(mixed())
        self.assertIn("apps/orders/application/<context>/usecase.txt", written)
        self.assertIn("apps/billing/application/<context>/usecase.txt", written)
        self.assertIn("In `apps/billing`, express agreed examples", written)


@unittest.skipUnless(checkout_packages.installed("toy"), "the toy package is not checked out")
class BackingServiceProseTest(unittest.TestCase):
    """The store's own sections, which say what each rung's gate does and does not prove."""

    def pages(self, apps: list[App]) -> tuple[str, str]:
        return readme("shop", "event-modelling", apps), documentation_files(
            "shop", "event-modelling", apps
        )["docs/gates.md"]

    def test_a_state_stored_project_describes_a_state_store_and_not_a_log(self) -> None:
        page, gates = self.pages(state_only())
        self.assertIn("### Postgres — the state store", page)
        self.assertNotIn("the event store", page)
        self.assertIn("repository contract is proved", gates)
        self.assertNotIn("event-store contract", gates)

    def test_a_mixed_project_describes_both_stores_on_the_one_postgres(self) -> None:
        """Same container, same `make migrate`, two guarantees — and a reader has to be able to tell which
        of them the concurrency test they are reading belongs to."""
        page, gates = self.pages(mixed())
        self.assertIn("### Postgres — the event store", page)
        self.assertIn("### Postgres — the state store", page)
        self.assertIn("event-store contract", gates)
        self.assertIn("repository contract is proved", gates)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
