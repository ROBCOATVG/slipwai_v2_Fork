"""The Ed25519 verifier, against RFC 8032's own vectors and against the ways a signature is wrong.

Hand-written cryptography is held to the standard's published answers or it is held to nothing: a verifier
that agrees with itself proves only that it is consistent. Section 7.1's vectors are the whole point of
this file — a key, a message and a signature that the RFC says go together, checked both ways round.

What is also here is every malformed input, because that is where a verifier gets interesting. The bytes a
`verify` is handed were chosen by whoever is trying to get something installed, and a verifier that raised
on one shape and answered `False` on another would be saying something with the shape of its failure that
the answer does not say.
"""
from __future__ import annotations

import binascii
import unittest

import checkout_packages  # noqa: F401

from slipwai import ed25519

#: RFC 8032, section 7.1: secret, public, message, signature. Hex, as the RFC prints them.
VECTORS = (
    ("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
     "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
     "",
     "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46b"
     "d25bf5f0595bbe24655141438e7a100b"),
    ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
     "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
     "72",
     "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c"
     "387b2eaeb4302aeeb00d291612bb0c00"),
    ("c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7",
     "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025",
     "af82",
     "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc659"
     "4a7c15e9716ed28dc027beceea1ec40a"),
    # The long one: a 1023-byte message, which is the vector that catches an implementation that only ever
    # hashed something short. Truncated here to the RFC's first and last bytes would prove nothing, so it
    # is the whole of it.
    ("f5e5767cf153319517630f226876b86c8160cc583bc013744c6bf255f5cc0ee5",
     "278117fc144c72340f67d0f2316e8386ceffbf2b2428c9c51fef7c597f1d426e",
     "08b8b2b733424243760fe426a4b54908632110a66c2f6591eabd3345e3e4eb98fa6e264bf09efe12ee50f8f54e9f77b1"
     "e355f6c50544e23fb1433ddf73be84d879de7c0046dc4996d9e773f4bc9efe5738829adb26c81b37c93a1b270b20329d"
     "658675fc6ea534e0810a4432826bf58c941efb65d57a338bbd2e26640f89ffbc1a858efcb8550ee3a5e1998bd177e93a"
     "7363c344fe6b199ee5d02e82d522c4feba15452f80288a821a579116ec6dad2b3b310da903401aa62100ab5d1a36553e"
     "06203b33890cc9b832f79ef80560ccb9a39ce767967ed628c6ad573cb116dbefefd75499da96bd68a8a97b928a8bbc10"
     "3b6621fcde2beca1231d206be6cd9ec7aff6f6c94fcd7204ed3455c68c83f4a41da4af2b74ef5c53f1d8ac70bdcb7ed1"
     "85ce81bd84359d44254d95629e9855a94a7c1958d1f8ada5d0532ed8a5aa3fb2d17ba70eb6248e594e1a2297acbbb39d"
     "502f1a8c6eb6f1ce22b3de1a1f40cc24554119a831a9aad6079cad88425de6bde1a9187ebb6092cf67bf2b13fd65f270"
     "88d78b7e883c8759d2c4f5c65adb7553878ad575f9fad878e80a0c9ba63bcbcc2732e69485bbc9c90bfbd62481d9089b"
     "eccf80cfe2df16a2cf65bd92dd597b0707e0917af48bbb75fed413d238f5555a7a569d80c3414a8d0859dc65a46128ba"
     "b27af87a71314f318c782b23ebfe808b82b0ce26401d2e22f04d83d1255dc51addd3b75a2b1ae0784504df543af8969b"
     "e3ea7082ff7fc9888c144da2af58429ec96031dbcad3dad9af0dcbaaaf268cb8fcffead94f3c7ca495e056a9b47acdb7"
     "51fb73e666c6c655ade8297297d07ad1ba5e43f1bca32301651339e22904cc8c42f58c30c04aafdb038dda0847dd988d"
     "cda6f3bfd15c4b4c4525004aa06eeff8ca61783aacec57fb3d1f92b0fe2fd1a85f6724517b65e614ad6808d6f6ee34df"
     "f7310fdc82aebfd904b01e1dc54b2927094b2db68d6f903b68401adebf5a7e08d78ff4ef5d63653a65040cf9bfd4aca7"
     "984a74d37145986780fc0b16ac451649de6188a7dbdf191f64b5fc5e2ab47b57f7f7276cd419c17a3ca8e1b939ae49e4"
     "88acba6b965610b5480109c8b17b80e1b7b750dfc7598d5d5011fd2dcc5600a32ef5b52a1ecc820e308aa342721aac09"
     "43bf6686b64b2579376504ccc493d97e6aed3fb0f9cd71a43dd497f01f17c0e2cb3797aa2a2f256656168e6c496afc5f"
     "b93246f6b1116398a346f1a641f3b041e989f7914f90cc2c7fff357876e506b50d334ba77c225bc307ba537152f3f161"
     "0e4eafe595f6d9d90d11faa933a15ef1369546868a7f3a45a96768d40fd9d03412c091c6315cf4fde7cb68606937380d"
     "b2eaaa707b4c4185c32eddcdd306705e4dc1ffc872eeee475a64dfac86aba41c0618983f8741c5ef68d3a101e8a3b8ca"
     "c60c905c15fc910840b94c00a0b9d0",
     "0aab4c900501b3e24d7cdf4663326a3a87df5e4843b2cbdb67cbf6e460fec350aa5371b1508f9f4528ecea23c436d94b"
     "5e8fcd4f681e30a6ac00a9704a188a03"),
)


def bytes_of(text: str) -> bytes:
    return binascii.unhexlify(text)


class VectorTest(unittest.TestCase):
    """RFC 8032 section 7.1, all four, in both directions."""

    def test_the_public_key_is_the_one_the_rfc_derives(self) -> None:
        for secret, public, _, _ in VECTORS:
            with self.subTest(key=public[:16]):
                self.assertEqual(ed25519.public_key(bytes_of(secret)), bytes_of(public))

    def test_the_signature_is_the_one_the_rfc_prints(self) -> None:
        """Ed25519 is deterministic, so there is one right answer and the RFC has written it down."""
        for secret, _, message, signature in VECTORS:
            with self.subTest(signature=signature[:16]):
                self.assertEqual(ed25519.sign(bytes_of(secret), bytes_of(message)), bytes_of(signature))

    def test_each_signature_verifies_against_its_key(self) -> None:
        for _, public, message, signature in VECTORS:
            with self.subTest(key=public[:16]):
                self.assertTrue(ed25519.verify(bytes_of(public), bytes_of(message), bytes_of(signature)))


class RefusalTest(unittest.TestCase):
    """Every way a signature is wrong, which is the half that matters."""

    def setUp(self) -> None:
        secret, public, message, signature = VECTORS[1]
        self.secret, self.public = bytes_of(secret), bytes_of(public)
        self.message, self.signature = bytes_of(message), bytes_of(signature)

    def test_a_changed_message_does_not_verify(self) -> None:
        """The whole of what a release signature is for: these bytes, not some other bytes."""
        self.assertFalse(ed25519.verify(self.public, self.message + b"\x00", self.signature))

    def test_another_key_does_not_verify(self) -> None:
        other = ed25519.public_key(bytes_of(VECTORS[2][0]))
        self.assertFalse(ed25519.verify(other, self.message, self.signature))

    def test_a_changed_signature_does_not_verify(self) -> None:
        for index in (0, 31, 32, 63):
            with self.subTest(byte=index):
                altered = bytearray(self.signature)
                altered[index] ^= 0x01
                self.assertFalse(ed25519.verify(self.public, self.message, bytes(altered)))

    def test_a_scalar_at_or_past_the_group_order_is_refused(self) -> None:
        """RFC 8032's own rule, and the one a naive implementation leaves out: `s` must be reduced."""
        over = self.signature[:32] + int.to_bytes(ed25519.Q, 32, "little")
        self.assertFalse(ed25519.verify(self.public, self.message, over))

    def test_nothing_malformed_raises(self) -> None:
        """The bytes were chosen by whoever wants this installed. Every wrong shape is the same answer."""
        for key, signature in ((b"", self.signature), (self.public, b""), (b"\xff" * 32, self.signature),
                               (self.public, b"\xff" * 64), (b"\x00" * 32, self.signature)):
            with self.subTest(key=len(key), signature=len(signature)):
                self.assertFalse(ed25519.verify(key, self.message, signature))

    def test_a_secret_of_the_wrong_length_is_a_refusal_and_not_a_signature(self) -> None:
        """The other direction: a publisher whose key file is wrong is told, not quietly signed with."""
        for wrong in (b"", b"\x00" * 31, b"\x00" * 33):
            with self.subTest(length=len(wrong)):
                with self.assertRaises(ValueError):
                    ed25519.sign(wrong, b"x")
                with self.assertRaises(ValueError):
                    ed25519.public_key(wrong)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
