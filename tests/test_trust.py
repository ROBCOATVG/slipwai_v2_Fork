"""Who this machine installs from, and the four states a release can be in.

Every store here is written into a temporary `SLIPWAI_HOME`, so the suite never reads or writes the one a
person has agreed to.
"""
from __future__ import annotations

import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import ed25519, trust
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
        """The one thing a signature must never be used to say is "signed" about one nobody looked at.

        `c2ln` is read as a Sigstore bundle, because it does not say `ed25519:` — and without the
        `slipwai[verify]` extra there is nothing here that can check one.
        """
        self.assertEqual(trust.state_of("ROBCOATVG", "c2ln", b"bytes"), trust.UNVERIFIED)

    def test_a_signature_that_is_checked_and_matches_is_verified(self) -> None:
        with mock.patch.object(trust, "check_signature", return_value=True):
            self.assertEqual(trust.state_of("ROBCOATVG", "c2ln", b"bytes"), trust.VERIFIED)

    def test_a_signature_that_is_checked_and_does_not_match_is_refused(self) -> None:
        with mock.patch.object(trust, "check_signature", return_value=False), \
                self.assertRaises(GenerationError) as refused:
            trust.state_of("ROBCOATVG", "c2ln", b"bytes")
        self.assertIn("does not match", str(refused.exception))

    def test_the_refusal_names_the_channel_as_well_as_the_publisher(self) -> None:
        """Two different things to go and look at: a publisher whose key has moved on, and a channel
        serving a file that is not the one the publisher signed."""
        with mock.patch.object(trust, "check_signature", return_value=False), \
                self.assertRaises(GenerationError) as refused:
            trust.state_of("ROBCOATVG", "c2ln", b"bytes", "the-org-channel")
        self.assertIn("ROBCOATVG", str(refused.exception))
        self.assertIn("the-org-channel", str(refused.exception))

    def test_the_four_states_each_have_a_phrase_so_every_command_says_them_alike(self) -> None:
        self.assertEqual(sorted(trust.SAID),
                         sorted([trust.VERIFIED, trust.UNVERIFIED, trust.UNSIGNED, trust.UNTRUSTED]))


class Ed25519Test(unittest.TestCase):
    """The private channel's half, end to end: a key in the store, a signature over the bytes.

    What is proved here is the join rather than the arithmetic — `test_ed25519.py` holds that against RFC
    8032. This is the three ways the join can be missing: no key, the wrong key, and the right key over
    bytes somebody changed afterwards.
    """

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.patch = mock.patch.dict(os.environ, {"SLIPWAI_HOME": str(self.home)})
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.secret = bytes(range(32))
        self.public = base64.b64encode(ed25519.public_key(self.secret)).decode("ascii")
        self.data = b"a release file, as the channel served it"
        self.signature = trust.ED25519 + base64.b64encode(
            ed25519.sign(self.secret, self.data)).decode("ascii")

    def test_a_release_signed_by_its_publisher_is_verified(self) -> None:
        trust.accept("the-org", "added", self.public)
        self.assertEqual(trust.state_of("the-org", self.signature, self.data), trust.VERIFIED)

    def test_the_same_release_with_a_byte_changed_is_refused(self) -> None:
        trust.accept("the-org", "added", self.public)
        with self.assertRaises(GenerationError) as refused:
            trust.state_of("the-org", self.signature, self.data + b"!", "the-org-channel")
        self.assertIn("does not match", str(refused.exception))
        self.assertIn("the-org", str(refused.exception))

    def test_a_publisher_this_machine_holds_no_key_for_is_unverified_and_not_refused(self) -> None:
        """`None` is not `False`. A machine that cannot check is not a machine that has caught someone."""
        trust.accept("the-org", "added")
        self.assertEqual(trust.state_of("the-org", self.signature, self.data), trust.UNVERIFIED)

    def test_another_publishers_key_does_not_verify_this_signature(self) -> None:
        trust.accept("the-org", "added", base64.b64encode(ed25519.public_key(bytes(range(1, 33)))).decode())
        with self.assertRaises(GenerationError):
            trust.state_of("the-org", self.signature, self.data)

    def test_a_signature_that_is_not_base64_is_unverified_rather_than_a_crash(self) -> None:
        trust.accept("the-org", "added", self.public)
        self.assertEqual(trust.state_of("the-org", trust.ED25519 + "not base64!", self.data),
                         trust.UNVERIFIED)

    def test_a_key_that_is_not_a_key_is_refused_when_it_is_written_rather_than_when_it_is_read(self) -> None:
        """So the person who typed it finds out, instead of every later install saying `unverified`."""
        with self.assertRaises(GenerationError) as refused:
            trust.accept("the-org", "added", "bm90IGEga2V5")
        self.assertIn("not an Ed25519 public key", str(refused.exception))


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
