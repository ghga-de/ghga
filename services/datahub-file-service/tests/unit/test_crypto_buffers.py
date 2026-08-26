# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for the part decryption/re-encryption buffer handling.

These helpers size their output buffers up front, so the sizes they derive have to
hold for partial trailing segments as well as segment-aligned input.
"""

import os
from collections.abc import Iterator
from math import ceil

import crypt4gh.lib
import pytest
from pydantic import SecretBytes

from dhfs.constants import ENCRYPTION_SECRET_LENGTH, NONCE_LENGTH, SEGMENT_OVERHEAD
from dhfs.core.interrogator import Interrogator
from tests.fixtures.interrogator import make_interrogator

SEGMENT = crypt4gh.lib.SEGMENT_SIZE
CIPHER_SEGMENT = crypt4gh.lib.CIPHER_SEGMENT_SIZE

# Sizes chosen to cover empty input, sub-segment input, exact segment multiples, and
#  multiples plus a remainder that lands in a partial trailing segment.
PLAINTEXT_SIZES = [
    0,
    1,
    SEGMENT - 1,
    SEGMENT,
    SEGMENT + 1,
    2 * SEGMENT,
    2 * SEGMENT + 12345,
]


@pytest.fixture(name="interrogator")
def interrogator_fixture() -> Iterator[Interrogator]:
    """An Interrogator with mocked-out collaborators - only crypto is exercised."""
    with make_interrogator() as interrogator:
        yield interrogator


@pytest.mark.parametrize("size", PLAINTEXT_SIZES)
def test_reencrypt_decrypt_round_trip(interrogator: Interrogator, size: int):
    """Re-encrypting then decrypting a part must return the original bytes."""
    secret = SecretBytes(os.urandom(ENCRYPTION_SECRET_LENGTH))
    plaintext = os.urandom(size)

    ciphertext = interrogator._reencrypt_part(
        decrypted_part=plaintext, new_secret=secret
    )
    recovered = interrogator._decrypt_part(encrypted_part=ciphertext, secret=secret)

    assert bytes(recovered) == plaintext


@pytest.mark.parametrize("size", PLAINTEXT_SIZES)
def test_reencrypted_size_matches_crypt4gh_framing(
    interrogator: Interrogator, size: int
):
    """Each encrypted segment must grow by exactly a nonce plus an auth tag.

    The part loop relies on this to keep S3 part numbers lined up with download ranges.
    """
    secret = SecretBytes(os.urandom(ENCRYPTION_SECRET_LENGTH))
    segments = ceil(size / SEGMENT)

    ciphertext = interrogator._reencrypt_part(
        decrypted_part=os.urandom(size), new_secret=secret
    )

    assert len(ciphertext) == size + SEGMENT_OVERHEAD * segments


@pytest.mark.parametrize("size", PLAINTEXT_SIZES)
def test_decrypt_accepts_any_buffer_type(interrogator: Interrogator, size: int):
    """Parts arrive as bytes from S3 but as bytearray from the re-encryption step."""
    secret = SecretBytes(os.urandom(ENCRYPTION_SECRET_LENGTH))
    plaintext = os.urandom(size)
    ciphertext = interrogator._reencrypt_part(
        decrypted_part=plaintext, new_secret=secret
    )

    for buffer in (ciphertext, bytearray(ciphertext), memoryview(ciphertext)):
        recovered = interrogator._decrypt_part(encrypted_part=buffer, secret=secret)
        assert bytes(recovered) == plaintext


def test_decrypt_part_raises_on_wrong_secret(interrogator: Interrogator):
    """A part that cannot be authenticated must surface as a DecryptionError."""
    secret = SecretBytes(os.urandom(ENCRYPTION_SECRET_LENGTH))
    wrong_secret = SecretBytes(os.urandom(ENCRYPTION_SECRET_LENGTH))
    ciphertext = interrogator._reencrypt_part(
        decrypted_part=os.urandom(SEGMENT + 99), new_secret=secret
    )

    with pytest.raises(Interrogator.DecryptionError):
        interrogator._decrypt_part(encrypted_part=ciphertext, secret=wrong_secret)


@pytest.mark.parametrize("size", PLAINTEXT_SIZES)
def test_decrypted_output_is_exactly_the_plaintext_length(
    interrogator: Interrogator, size: int
):
    """The preallocated buffer is returned whole, so it has to be filled exactly."""
    secret = SecretBytes(os.urandom(ENCRYPTION_SECRET_LENGTH))
    ciphertext = interrogator._reencrypt_part(
        decrypted_part=os.urandom(size), new_secret=secret
    )

    recovered = interrogator._decrypt_part(encrypted_part=ciphertext, secret=secret)

    assert len(recovered) == size


@pytest.mark.parametrize(
    "part_size",
    [1, NONCE_LENGTH, SEGMENT_OVERHEAD - 1],
    ids=["single byte", "nonce only", "one short of a nonce and tag"],
)
def test_decrypt_rejects_parts_too_short_to_be_framed(
    interrogator: Interrogator, part_size: int
):
    """A part below the per-segment overhead must fail as DecryptionError.

    Escaping as a bare ValueError would get it classified as merely retryable.
    """
    secret = SecretBytes(os.urandom(ENCRYPTION_SECRET_LENGTH))

    with pytest.raises(Interrogator.DecryptionError):
        interrogator._decrypt_part(encrypted_part=os.urandom(part_size), secret=secret)


def test_decrypt_rejects_a_truncated_part(interrogator: Interrogator):
    """A part cut short mid-segment must not decrypt to a shorter plaintext."""
    secret = SecretBytes(os.urandom(ENCRYPTION_SECRET_LENGTH))
    ciphertext = interrogator._reencrypt_part(
        decrypted_part=os.urandom(2 * SEGMENT), new_secret=secret
    )

    with pytest.raises(Interrogator.DecryptionError):
        interrogator._decrypt_part(
            encrypted_part=ciphertext[: len(ciphertext) - 100], secret=secret
        )


def test_decrypt_rejects_a_corrupted_part(interrogator: Interrogator):
    """A flipped byte must fail authentication rather than yield wrong plaintext."""
    secret = SecretBytes(os.urandom(ENCRYPTION_SECRET_LENGTH))
    ciphertext = bytearray(
        interrogator._reencrypt_part(
            decrypted_part=os.urandom(SEGMENT + 500), new_secret=secret
        )
    )
    ciphertext[len(ciphertext) // 2] ^= 0xFF

    with pytest.raises(Interrogator.DecryptionError):
        interrogator._decrypt_part(encrypted_part=ciphertext, secret=secret)


def test_reencryption_uses_a_fresh_nonce_per_segment(interrogator: Interrogator):
    """Reusing a nonce under one key would break ChaCha20-Poly1305."""
    secret = SecretBytes(os.urandom(ENCRYPTION_SECRET_LENGTH))
    segment_count = 4

    ciphertext = interrogator._reencrypt_part(
        decrypted_part=os.urandom(segment_count * SEGMENT), new_secret=secret
    )

    nonces = {
        bytes(ciphertext[i * CIPHER_SEGMENT : i * CIPHER_SEGMENT + NONCE_LENGTH])
        for i in range(segment_count)
    }
    assert len(nonces) == segment_count
