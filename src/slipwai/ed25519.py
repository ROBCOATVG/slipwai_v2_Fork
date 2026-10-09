"""Ed25519 signing and verification, RFC 8032, in the standard library alone.

The keel ships with no dependencies, and an install that needed one would be an install that fails on the
machine where it matters. Python's standard library has no X.509 and no ECDSA, so a Sigstore bundle cannot
be checked here at all — but Ed25519 is arithmetic over one curve with one hash, and RFC 8032's own
reference implementation is ninety lines of it. That is what this is: the reference, written out, with the
RFC's test vectors as the suite.

**This is hand-written cryptography and that is a thing to be unhappy about.** Two things make it the right
trade anyway, and both are about where it is used (plan 6.5, decided 2026-10-08). It verifies a *private*
channel, where an organisation holding its own key is the normal arrangement and the keyless argument does
not apply; the public channel is Sigstore through the `slipwai[verify]` extra, which is a real library doing
a real X.509 job. And what it is asked is the narrow question — *is this signature this key's over these
bytes* — with the digest and TLS already answering everything else. There is no key agreement here, no
parsing of an attacker-controlled structure beyond thirty-two bytes of point, and no secret-dependent path
that a timing attack could read: verification touches no secret at all.

`sign` is here because a publisher has to produce what `verify` reads, and a signer that lived somewhere
else would be a second implementation of the same arithmetic. It is constant-time in nothing, and says so:
a signing key belongs on a machine the publisher controls, which is the machine `slipwai package release`
runs on.
"""
from __future__ import annotations

import hashlib

#: The field, the group order, and the curve constant. RFC 8032, section 5.1.
P = 2**255 - 19
Q = 2**252 + 27742317777372353535851937790883648493
#: Where a key and a signature are fixed-width. Thirty-two bytes of compressed point, sixty-four of signature.
KEY_BYTES = 32
SIGNATURE_BYTES = 64

_D = -121665 * pow(121666, P - 2, P) % P
_SQRT_MINUS_1 = pow(2, (P - 1) // 4, P)

#: A point in extended homogeneous coordinates, `(x, y, z, t)`, and the neutral element.
Point = tuple[int, int, int, int]
NEUTRAL: Point = (0, 1, 1, 0)


def _sha512(data: bytes) -> bytes:
    return hashlib.sha512(data).digest()


def _sha512_modq(data: bytes) -> int:
    return int.from_bytes(_sha512(data), "little") % Q


def _recover_x(y: int, sign: int) -> int | None:
    """The x of the point with this y and this sign bit, or None where no such point is on the curve."""
    if y >= P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, P - 2, P) % P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P != 0:
        x = x * _SQRT_MINUS_1 % P
    if (x * x - x2) % P != 0:
        return None
    return P - x if (x & 1) != sign else x


def _base() -> Point:
    y = 4 * pow(5, P - 2, P) % P
    x = _recover_x(y, 0)
    assert x is not None  # the curve's own base point; a None here would mean the constants are wrong
    return (x, y, 1, x * y % P)


BASE = _base()


def _add(first: Point, second: Point) -> Point:
    """The twisted-Edwards addition of RFC 8032, which is the same formula for a double."""
    a = (first[1] - first[0]) * (second[1] - second[0]) % P
    b = (first[1] + first[0]) * (second[1] + second[0]) % P
    c = 2 * first[3] * second[3] * _D % P
    d = 2 * first[2] * second[2] % P
    e, f, g, h = b - a, d - c, d + c, b + a
    return (e * f % P, g * h % P, f * g % P, e * h % P)


def _multiply(scalar: int, point: Point) -> Point:
    """Double-and-add. Not constant-time, and never given a secret in `verify`."""
    found = NEUTRAL
    while scalar > 0:
        if scalar & 1:
            found = _add(found, point)
        point = _add(point, point)
        scalar >>= 1
    return found


def _equal(first: Point, second: Point) -> bool:
    """Whether two projective points are the same point, compared without inverting either."""
    return ((first[0] * second[2] - second[0] * first[2]) % P == 0
            and (first[1] * second[2] - second[1] * first[2]) % P == 0)


def _compress(point: Point) -> bytes:
    inverse = pow(point[2], P - 2, P)
    x, y = point[0] * inverse % P, point[1] * inverse % P
    return int.to_bytes(y | ((x & 1) << 255), KEY_BYTES, "little")


def _decompress(data: bytes) -> Point | None:
    """The point thirty-two bytes encode, or None where they encode none — which is a signature's to refuse."""
    if len(data) != KEY_BYTES:
        return None
    held = int.from_bytes(data, "little")
    sign = held >> 255
    y = held & ((1 << 255) - 1)
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % P)


def _expand(secret: bytes) -> tuple[int, bytes]:
    hashed = _sha512(secret)
    scalar = int.from_bytes(hashed[:KEY_BYTES], "little")
    scalar &= (1 << 254) - 8
    scalar |= 1 << 254
    return scalar, hashed[KEY_BYTES:]


def public_key(secret: bytes) -> bytes:
    """The public key for a thirty-two byte seed, which is what a publisher publishes."""
    if len(secret) != KEY_BYTES:
        raise ValueError(f"an Ed25519 secret key is {KEY_BYTES} bytes, and this is {len(secret)}")
    scalar, _ = _expand(secret)
    return _compress(_multiply(scalar, BASE))


def sign(secret: bytes, message: bytes) -> bytes:
    """The sixty-four byte signature of `message` under the seed `secret`."""
    if len(secret) != KEY_BYTES:
        raise ValueError(f"an Ed25519 secret key is {KEY_BYTES} bytes, and this is {len(secret)}")
    scalar, prefix = _expand(secret)
    key = _compress(_multiply(scalar, BASE))
    nonce = _sha512_modq(prefix + message)
    commitment = _compress(_multiply(nonce, BASE))
    challenge = _sha512_modq(commitment + key + message)
    return commitment + int.to_bytes((nonce + challenge * scalar) % Q, KEY_BYTES, "little")


def verify(key: bytes, message: bytes, signature: bytes) -> bool:
    """Whether `signature` is `key`'s over `message`. False for anything malformed — never an exception.

    A caller is asking a yes-or-no question about bytes somebody else chose, and every way those bytes can
    be wrong is the same answer: a key that is not a point, a commitment that is not a point, a scalar at or
    past the group order. Raising on one of them and returning False on the next would make the shape of the
    failure say something the answer does not.
    """
    if len(key) != KEY_BYTES or len(signature) != SIGNATURE_BYTES:
        return False
    point = _decompress(key)
    commitment = _decompress(signature[:KEY_BYTES])
    if point is None or commitment is None:
        return False
    scalar = int.from_bytes(signature[KEY_BYTES:], "little")
    if scalar >= Q:
        return False
    challenge = _sha512_modq(signature[:KEY_BYTES] + key + message)
    return _equal(_multiply(scalar, BASE), _add(commitment, _multiply(challenge, point)))
