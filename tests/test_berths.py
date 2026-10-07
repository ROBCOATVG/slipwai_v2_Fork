"""A berth's allocation: arithmetic rather than a table somebody maintains.

In the experiment and in MANDA this was an operator's job and lived in their head — five berths on one
machine, the port numbers chosen by hand, a load average of 198 when nobody was counting. What goes wrong
is not dramatic: two berths take one port, one fails to start, and the failure reads as a broken service
rather than as a collision.

So a berth's ports fall out of its index and its database out of its name. Nobody chooses a number, so
nobody chooses the same number twice — and `collisions` checks that, because "by construction" is a claim
like any other.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai import berths
from slipwai.backends import SERVICE_PORT, WEB_PORT


class AllocationTest(unittest.TestCase):
    def test_two_berths_never_share_a_port(self) -> None:
        allocated = berths.allocate(["orca", "narwhal"])
        self.assertEqual(berths.collisions(allocated), [])
        self.assertEqual(set(allocated[0].ports) & set(allocated[1].ports), set())

    def test_two_berths_never_share_a_database(self) -> None:
        """A migration that drops a table drops it for everybody in a shared one, and the failure arrives
        in a fairway that changed nothing."""
        allocated = berths.allocate(["orca", "narwhal"])
        self.assertNotEqual(allocated[0].database, allocated[1].database)

    def test_many_berths_still_collide_nowhere(self) -> None:
        self.assertEqual(berths.collisions(berths.allocate([f"b{n}" for n in range(12)])), [])

    def test_a_block_starts_above_what_a_project_uses_outside_a_berth(self) -> None:
        """So a berth never collides with a project started the ordinary way."""
        first = berths.allocate(["orca"])[0]
        self.assertGreater(min(first.ports), max(SERVICE_PORT, WEB_PORT))

    def test_a_block_has_room_for_more_than_today_s_services(self) -> None:
        """A block exactly big enough today is a block too small at the next service."""
        self.assertGreaterEqual(len(berths.allocate(["orca"])[0].ports), 20)

    def test_everything_but_the_name_and_the_index_is_derived(self) -> None:
        one = berths.berth("orca", 0)
        self.assertEqual(one.database, berths.database_of("orca"))
        self.assertIn("orca", one.scratch)
        self.assertIn("orca", one.worktree)


class NameTest(unittest.TestCase):
    def test_a_name_is_held_to_what_a_database_and_a_directory_both_allow(self) -> None:
        for bad in ("Orca", "1orca", "orca_one", "orca!", "", "o" * 40):
            with self.subTest(name=bad), self.assertRaises(ValueError):
                berths.named(bad)

    def test_the_refusal_says_why_the_rule_is_what_it_is(self) -> None:
        with self.assertRaises(ValueError) as refused:
            berths.named("Orca")
        self.assertIn("becomes a database name", str(refused.exception))

    def test_a_hyphen_is_allowed_in_a_name_and_not_in_a_database(self) -> None:
        self.assertEqual(berths.named("orca-two"), "orca-two")
        self.assertEqual(berths.database_of("orca-two"), "app_orca_two")


class CollisionTest(unittest.TestCase):
    def test_a_collision_is_reported_with_both_berths_named(self) -> None:
        """The check exists because the arithmetic claim is still a claim."""
        same = [berths.berth("orca", 0), berths.berth("narwhal", 0)]
        found = berths.collisions(same)
        self.assertTrue(found)
        self.assertIn("orca", found[0])
        self.assertIn("narwhal", found[0])


class CredentialTest(unittest.TestCase):
    def test_a_berth_record_holds_no_credential_field(self) -> None:
        """A berth that held a token would be a sandbox with a way out of it."""
        fields = set(vars(berths.berth("orca", 0)))
        for forbidden in ("token", "credential", "secret", "key", "password"):
            with self.subTest(field=forbidden):
                self.assertNotIn(forbidden, fields)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
