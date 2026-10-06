"""What a language package may add to the catalogue, and what it may not.

The keel declares the axes and the answers that are infrastructure: a Postgres event store is Postgres
whichever language talks to it. An answer named after a library — `fastapi`, `spring-web`, `fastify` —
is a language's framework, and a keel that declared one would be a keel a new language has to be edited
into. Those belong to the package that implements them.

The toy package brings `http/toy-serve`, so this path is exercised by the keel's own gate on every
commit rather than only when a real language is installed.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import PRUNER, ROOT
from slipwai.catalog import CATALOG
from slipwai.catalog_options import declare_options
from slipwai.language_directory import Package

KEEL = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))


def package(name: str, axes: dict) -> Package:
    return Package(name, Path(f"/packages/{name}"),
                   {"name": name, "core": ">=9.0,<10", "order": 50, "family": name, "backends": {}, "axes": axes})


def option(**changes: object) -> dict:
    return {"label": "An option", "capabilities": [], "features": [], "containers": [],
            "migrations": False, "integration-suite": False, "targets": ["none"], **changes}


class TheKeelsOwnTest(unittest.TestCase):
    def test_the_keel_declares_no_framework_on_the_http_axis(self) -> None:
        """The line issue #26 drew. `none` is the keel's answer — no inbound HTTP is not a language's."""
        self.assertEqual(set(KEEL["axes"]["http"]["options"]), {"none"})

    def test_the_keel_still_declares_the_infrastructure_answers(self) -> None:
        """Postgres is Postgres whoever talks to it, and the keel ships the files for it."""
        self.assertEqual(set(KEEL["axes"]["event-store"]["options"]), {"memory", "sqlite", "postgres"})
        self.assertIn("keycloak", KEEL["axes"]["auth"]["options"])

    def test_the_keels_pruner_carries_no_framework_either(self) -> None:
        for name in ("fastapi", "fastify", "net-http", "quarkus-rest", "spring-web"):
            with self.subTest(framework=name):
                self.assertNotIn(name, PRUNER.FEATURES)
                self.assertNotIn(name, PRUNER.AXES["http"]["options"])

    def test_an_axis_whose_answers_are_all_a_languages_is_valid_with_one_option(self) -> None:
        """A keel with no package installed offers a short menu, not a broken catalogue."""
        self.assertEqual(len(KEEL["axes"]["http"]["options"]), 1)


class BroughtTest(unittest.TestCase):
    def test_the_toy_brings_its_own_transport_and_the_merge_takes_it(self) -> None:
        self.assertIn("toy-serve", CATALOG["axes"]["http"]["options"])
        self.assertEqual(CATALOG["axes"]["http"]["options"]["toy-serve"]["backends"], ["toy-plain"])

    def test_a_brought_option_arrives_whole(self) -> None:
        """Label, capabilities, the feature that owns its files, and where it is offered."""
        brought = CATALOG["axes"]["http"]["options"]["toy-serve"]
        self.assertEqual(brought["capabilities"], ["http-toy-serve"])
        self.assertEqual(brought["features"], ["toy-serve"])
        self.assertTrue(brought["label"])


class RefusalTest(unittest.TestCase):
    def refuse(self, *packages: Package) -> dict[str, str]:
        merged = json.loads(json.dumps(KEEL))
        return declare_options(merged, list(packages))

    def test_two_packages_declaring_one_option_are_both_refused_and_each_names_the_other(self) -> None:
        """One declarer per option, for the reason one setter per mark exists: nothing here chooses."""
        refused = self.refuse(package("a", {"http": {"dup": option()}}),
                              package("b", {"http": {"dup": option()}}))
        self.assertEqual(set(refused), {"a", "b"})
        self.assertIn("b", refused["a"])
        self.assertIn("a", refused["b"])

    def test_an_option_the_keel_already_declares_is_refused(self) -> None:
        """The keel's are the ones every package was built against; a package may not redefine one."""
        refused = self.refuse(package("a", {"event-store": {"postgres": option()}}))
        self.assertIn("already declares", refused["a"])

    def test_an_axis_the_keel_does_not_have_is_refused(self) -> None:
        refused = self.refuse(package("a", {"cache": {"redis": option()}}))
        self.assertIn("no cache axis", refused["a"])

    def test_a_package_that_brings_nothing_is_not_refused(self) -> None:
        self.assertEqual(self.refuse(package("a", {})), {})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
