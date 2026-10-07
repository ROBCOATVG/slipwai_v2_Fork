"""Who this machine installs from, and the four states a release can be in.

Every store here is written into a temporary `SLIPWAI_HOME`, so the suite never reads or writes the one a
person has agreed to.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import trust
from slipwai.errors import GenerationError


class StoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.patch = mock.patch.dict(os.environ, {"SLIPWAI_HOME": str(self.home)})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_the_keel_s_own_publisher_is_there_before_anything_is_written(self) -> None:
        self.assertTrue(trust.trusted("ROBCOATVG"))

    def test_it_is_a_row_and_not_a_rule_so_it_can_be_removed(self) -> None:
        """The difference between a default and a rule is whether a person can change their mind."""
        trust.forget("ROBCOATVG")
        self.assertFalse(trust.trusted("ROBCOATVG"))

    def test_accepting_one_is_remembered(self) -> None:
        trust.accept("someone")
        self.assertTrue(trust.trusted("someone"))
        held = json.loads((self.home / "trust.json").read_text(encoding="utf-8"))
        self.assertIn("when", held["publishers"]["someone"])

    def test_a_publisher_with_no_name_cannot_be_accepted(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            trust.accept("")
        self.assertIn("nothing to agree to", str(refused.exception))

    def test_removing_one_that_is_not_there_says_what_is(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            trust.forget("stranger")
        self.assertIn("ROBCOATVG", str(refused.exception))

    def test_a_store_that_cannot_be_read_is_refused_and_never_replaced(self) -> None:
        """It is the record of what a person agreed to; starting again from the seed would drop all of it."""
        (self.home / "trust.json").write_text("{not json", encoding="utf-8")
        with self.assertRaises(GenerationError) as refused:
            trust.publishers()
        self.assertIn("Move it aside", str(refused.exception).replace("Fix it or move it aside",
                                                                     "Move it aside"))


class StateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.patch = mock.patch.dict(os.environ, {"SLIPWAI_HOME": str(self.home)})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_an_accepted_publisher_with_no_signature_is_unsigned(self) -> None:
        self.assertEqual(trust.state_of("ROBCOATVG", ""), trust.UNSIGNED)

    def test_an_unaccepted_publisher_is_untrusted_whatever_it_carries(self) -> None:
        self.assertEqual(trust.state_of("stranger", "c2ln"), trust.UNTRUSTED)

    def test_a_signature_this_copy_cannot_check_is_unverified_and_not_verified(self) -> None:
        """The one thing a signature must never be used to say is "signed" about one nobody looked at."""
        self.assertEqual(trust.state_of("ROBCOATVG", "c2ln", b"bytes"), trust.UNVERIFIED)

    def test_a_signature_that_is_checked_and_matches_is_verified(self) -> None:
        with mock.patch.object(trust, "check_signature", return_value=True):
            self.assertEqual(trust.state_of("ROBCOATVG", "c2ln", b"bytes"), trust.VERIFIED)

    def test_a_signature_that_is_checked_and_does_not_match_is_refused(self) -> None:
        with mock.patch.object(trust, "check_signature", return_value=False), \
                self.assertRaises(GenerationError) as refused:
            trust.state_of("ROBCOATVG", "c2ln", b"bytes")
        self.assertIn("does not match", str(refused.exception))

    def test_the_four_states_each_have_a_phrase_so_every_command_says_them_alike(self) -> None:
        self.assertEqual(sorted(trust.SAID),
                         sorted([trust.VERIFIED, trust.UNVERIFIED, trust.UNSIGNED, trust.UNTRUSTED]))


class AdmittedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.patch = mock.patch.dict(os.environ, {"SLIPWAI_HOME": str(self.home)})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_a_named_publisher_nobody_accepted_is_refused_with_both_ways_to_accept(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            trust.admitted("lens", "stranger", "")
        said = str(refused.exception)
        self.assertIn("--accept-publisher", said)
        self.assertIn("trust add stranger", said)

    def test_confirming_accepts_them_once_and_the_next_release_is_silent(self) -> None:
        trust.admitted("lens", "stranger", "", confirm=True)
        self.assertEqual(trust.admitted("lens", "stranger", ""), trust.UNSIGNED)

    def test_a_package_whose_index_names_no_publisher_is_not_refused(self) -> None:
        """A `file:` channel on a person's own machine names none, and so does every index of version 1."""
        self.assertEqual(trust.admitted("lens", "", ""), trust.UNSIGNED)


if __name__ == "__main__":
    unittest.main()
