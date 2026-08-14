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
from math import ceil
from unittest.mock import MagicMock

import crypt4gh.lib
import pytest
from pydantic import SecretBytes

from dhfs.constants import ENCRYPTION_SECRET_LENGTH, NONCE_LENGTH, SEGMENT_OVERHEAD
from dhfs.core.interrogator import Interrogator
from tests.fixtures.config import get_config
from tests.fixtures.utils import DHFS_CRYPT4GH_PRIVATE_KEY_PATH

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
def interrogator_fixture() -> Interrogator:
    """An Interrogator with mocked-out collaborators - only crypto is exercised."""
    config = get_config(
        data_hub_crypt4gh_private_key_path=DHFS_CRYPT4GH_PRIVATE_KEY_PATH
    )
    return Interrogator(
        config=config, central_client=MagicMock(), s3_client=MagicMock()
    )


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

    The part-processing loop relies on a re-encrypted part being the same size as the
    encrypted part it came from, so that S3 part numbers line up with download ranges.
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
