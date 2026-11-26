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

"""Unit tests for Crypt4GHEncryptor"""

import base64
import hashlib
import io
import os
from collections import deque
from pathlib import Path

import crypt4gh.keys
import crypt4gh.lib
import pytest

from ghga_connector import exceptions
from ghga_connector.constants import (
    ENVELOPE_SIZE,
    MAX_ALIGNED_PART_SIZE,
    MIN_ALIGNED_PART_SIZE,
)
from ghga_connector.core.crypt.encryption import Crypt4GHEncryptor
from ghga_connector.core.uploading.structs import CoreFileInfo
from ghga_connector.core.utils import get_private_key
from tests.fixtures.utils import PRIVATE_KEY_FILE, PUBLIC_KEY_FILE, TEST_STORAGE_ALIAS1

SEGMENT_SIZE = crypt4gh.lib.SEGMENT_SIZE
CIPHER_SEGMENT_SIZE = crypt4gh.lib.CIPHER_SEGMENT_SIZE


@pytest.fixture()
def private_key(monkeypatch: pytest.MonkeyPatch):
    """Load the test private key.

    No need to patch make_passphrase_callback() because PRIVATE_KEY_FILE is unencrypted.
    """
    return get_private_key(PRIVATE_KEY_FILE)


@pytest.fixture(autouse=True)
def patch_ghga_pubkey(monkeypatch):
    """Make the encryptor use the test public key instead of the GHGA production key."""
    pubkey = crypt4gh.keys.get_public_key(PUBLIC_KEY_FILE)
    monkeypatch.setattr(
        "ghga_connector.core.crypt.encryption.get_crypt4gh_public_key",
        lambda storage_alias: base64.b64encode(pubkey).decode("utf-8"),
    )


def make_encryptor(
    private_key, file_size: int, part_size: int | None = None
) -> Crypt4GHEncryptor:
    """Create a Crypt4GHEncryptor with the given part_size, else with part_size set
    to half the file size, if possible.
    """
    if part_size is None:
        # Keep part_size within the min and max aligned boundaries
        part_size = max(MIN_ALIGNED_PART_SIZE, file_size // 2)
        part_size = min(part_size, MAX_ALIGNED_PART_SIZE)
    return Crypt4GHEncryptor(
        part_size=part_size,
        my_private_key=private_key,
        file_size=file_size,
        storage_alias=TEST_STORAGE_ALIAS1,
    )


def run_process_file(
    encryptor: Crypt4GHEncryptor, data: bytes
) -> list[tuple[int, bytes]]:
    """Run process_file on in-memory bytes and collect all yielded (part_number, content) tuples."""
    return list(encryptor.process_file(file=io.BytesIO(data)))  # type: ignore


def test_process_file_total_bytes_match_encrypted_size(private_key):
    """Make sure the sum of all yielded part sizes equals the full encrypted_size."""
    file_data = os.urandom(2 * MIN_ALIGNED_PART_SIZE + 100)
    core_info = CoreFileInfo(
        alias="x", path=Path("/dev/null"), decrypted_size=len(file_data)
    )
    encryptor = make_encryptor(private_key, file_size=len(file_data))
    parts = run_process_file(encryptor, file_data)
    assert sum(len(content) for _, content in parts) == core_info.encrypted_size


def test_process_file_ciphertext_size_matches_expected(private_key):
    """Make sure get_ciphertext_size() equals expected_ciphertext_size after processing."""
    file_data = os.urandom(3 * MIN_ALIGNED_PART_SIZE + 77)
    encryptor = make_encryptor(private_key, file_size=len(file_data))
    run_process_file(encryptor, file_data)
    assert encryptor.get_ciphertext_size() == encryptor.expected_ciphertext_size


def test_process_file_raises_on_ciphertext_size_mismatch(private_key):
    """Make sure CiphertextSizeMismatch is raised when expected_ciphertext_size is tampered with."""
    file_data = os.urandom(MIN_ALIGNED_PART_SIZE)
    encryptor = make_encryptor(private_key, file_size=len(file_data))
    encryptor.expected_ciphertext_size += 1  # force a mismatch
    with pytest.raises(exceptions.CiphertextSizeMismatch):
        run_process_file(encryptor, file_data)


def test_process_file_unencrypted_checksum_matches_input(private_key):
    """Make sure the unencrypted SHA256 checksum after processing equals SHA256 of the original data."""
    file_data = os.urandom(MIN_ALIGNED_PART_SIZE + 200)
    encryptor = make_encryptor(private_key, file_size=len(file_data))
    run_process_file(encryptor, file_data)
    assert (
        encryptor.checksums.decrypted_sha256.hexdigest()
        == hashlib.sha256(file_data).hexdigest()
    )


def test_process_file_yields_sequential_part_numbers(private_key):
    """Regression test: process_file must yield sequential S3 part numbers (1, 2, 3, …).

    The bug: process_file used the plaintext-file-chunk index (from enumerate) as the
    S3 PartNumber.  When a trailing chunk is too small to push the upload buffer past
    part_size, that iteration's index is consumed without a yield.  The post-loop then
    does `part_number += 1` from that stale index, skipping a number, which causes S3
    to receive a part with a PartNumber higher than the total number of parts uploaded,
    ultimately causing multipart-upload validation to fail or, worse, silently assemble
    a corrupt object.

    How to reproduce:
    - part_size = 2 * CIPHER_SEGMENT_SIZE (131 128 bytes)
    - file size = part_size + 1              (131 129 bytes)

    Trace through the original code (envelope is 124 B and stays at the front of
    upload_buffer until it gets yielded as part of the first part):
      Read 1 (131 128 B plaintext): 2 complete crypt4gh segments consume 131 072 B
        -> 131 128 encrypted bytes; 56 B remainder in unprocessed_bytes
        -> upload_buffer == envelope (124) + 131 128 = 131 252 >= part_size
        -> yield (part_number=1, first 131 128 B) ✓
        -> upload_buffer trimmed to the trailing 124 B
      Read 2 (1 B): combined with 56 B remainder = 57 B < SEGMENT_SIZE
        -> 0 complete segments -> 0 encrypted bytes -> buffer stays at 124 B
        -> 124 < part_size -> NO yield  (but enumerate's part_number advances to 2!)
      Post-loop: encrypt the 57-B incomplete segment -> 85 B
        -> upload_buffer = 124 + 85 = 209 B  -> skip the while loop
        -> part_number += 1 -> part_number = 3 -> yield (3, 209 B)  <-- BUG

    After the fix (sequential s3_part_number counter):
      Same reads, but the post-loop yields (s3_part_number=2, 209 B)  <-- CORRECT
    """
    # part_size = exactly 2 cipher segments so that the first read fills the buffer
    # to precisely part_size (plus envelope), and the one extra byte forces a
    # second (partial) read whose remainder never satisfies a full segment.
    part_size = 2 * CIPHER_SEGMENT_SIZE  # 131 128 bytes
    file_size = part_size + 1  # 131 129 bytes

    encryptor = make_encryptor(private_key, file_size=file_size, part_size=part_size)
    yielded_part_numbers = [
        pn for pn, _ in run_process_file(encryptor, b"x" * file_size)
    ]

    expected = list(range(1, len(yielded_part_numbers) + 1))
    assert yielded_part_numbers == expected, (
        f"'process_file' yielded non-sequential S3 part numbers: {yielded_part_numbers} "
        f"(expected {expected}).\nGaps in PartNumbers cause multipart-upload failures "
        "or silent data corruption."
    )


# A part of exactly two cipher segments, as the regression test above uses
SMALL_PART_SIZE = 2 * CIPHER_SEGMENT_SIZE


def decrypt_parts(private_key, parts: list[tuple[int, bytearray]]) -> bytes:
    """Join the parts and decrypt them with crypt4gh as the data hub would."""
    decrypted = io.BytesIO()
    crypt4gh.lib.decrypt(
        [(0, private_key.get_secret_value(), None)],
        io.BytesIO(b"".join(part for _, part in parts)),
        decrypted,
    )
    return decrypted.getvalue()


class ShortReads(io.BytesIO):
    """A file that never returns more than a few bytes per read."""

    def readinto(self, buffer) -> int:
        """Read at most 1000 bytes."""
        return super().readinto(memoryview(buffer)[:1000])


@pytest.mark.parametrize(
    "file_size",
    [
        1,
        SEGMENT_SIZE - 1,
        SEGMENT_SIZE,
        SEGMENT_SIZE + 1,
        # the envelope pushes the second segment across the end of the first part
        2 * SEGMENT_SIZE,
        # exactly one part: the envelope and two segments fill it
        SMALL_PART_SIZE - ENVELOPE_SIZE - 2 * (CIPHER_SEGMENT_SIZE - SEGMENT_SIZE),
        5 * SMALL_PART_SIZE + 12345,
    ],
)
@pytest.mark.parametrize("file_class", [io.BytesIO, ShortReads])
def test_process_file_decrypts_to_input(private_key, file_size: int, file_class):
    """Make sure the joined parts decrypt to the input, that every part but the last
    is full, and that the parts and the plaintext checksum add up.
    """
    file_data = os.urandom(file_size)
    encryptor = make_encryptor(
        private_key, file_size=file_size, part_size=SMALL_PART_SIZE
    )
    parts = list(encryptor.process_file(file=file_class(file_data)))

    assert decrypt_parts(private_key, parts) == file_data
    total = CoreFileInfo(
        alias="x", path=Path("/dev/null"), decrypted_size=file_size
    ).encrypted_size
    sizes = [len(part) for _, part in parts]
    assert sum(sizes) == total
    assert sizes[:-1] == [SMALL_PART_SIZE] * (len(sizes) - 1)
    assert len(sizes) == -(-total // SMALL_PART_SIZE)
    assert [number for number, _ in parts] == list(range(1, len(parts) + 1))
    assert (
        encryptor.checksums.decrypted_sha256.hexdigest()
        == hashlib.sha256(file_data).hexdigest()
    )


def test_process_file_raises_when_file_is_longer_than_announced(private_key):
    """Make sure a file that grew after its size was taken fails the size check."""
    file_data = os.urandom(3 * SEGMENT_SIZE)
    encryptor = make_encryptor(
        private_key, file_size=len(file_data) - 10, part_size=SMALL_PART_SIZE
    )
    with pytest.raises(exceptions.CiphertextSizeMismatch):
        run_process_file(encryptor, file_data)


# The envelope and six segments fill exactly three parts of SMALL_PART_SIZE
THREE_PARTS_FILE_SIZE = (
    3 * SMALL_PART_SIZE - ENVELOPE_SIZE - 6 * (CIPHER_SEGMENT_SIZE - SEGMENT_SIZE)
)


@pytest.mark.parametrize("in_flight", [1, 3])
@pytest.mark.parametrize("part_size", [SMALL_PART_SIZE, SMALL_PART_SIZE + 7])
@pytest.mark.parametrize(
    "file_size", [1, THREE_PARTS_FILE_SIZE, 5 * SMALL_PART_SIZE + 12345]
)
def test_process_file_reuses_parts_given_back(
    private_key, in_flight: int, part_size: int, file_size: int
):
    """Make sure parts given back are reused for the next parts without touching a
    part still in flight, that the last part comes at its exact size, and that no
    buffer is kept once the file needs no more.

    A part is read only when it is given back, as the upload does, so a buffer
    reused too early would garble the output.
    """
    file_data = os.urandom(file_size)
    encryptor = make_encryptor(private_key, file_size=file_size, part_size=part_size)
    yielded: list[bytearray] = []
    held: deque[tuple[int, bytearray]] = deque()
    sent: list[tuple[int, bytes]] = []

    def send_oldest() -> None:
        number, part = held.popleft()
        sent.append((number, bytes(part)))
        encryptor.give_back(part)

    file = io.BytesIO(file_data)
    for number, part in encryptor.process_file(file=file):  # type: ignore[arg-type]
        yielded.append(part)
        held.append((number, part))
        if len(held) == in_flight:
            send_oldest()
    while held:
        send_oldest()

    assert decrypt_parts(private_key, sent) == file_data  # type: ignore[arg-type]
    total = encryptor.expected_ciphertext_size
    sizes = [len(part) for _, part in sent]
    assert sizes[:-1] == [part_size] * (len(sizes) - 1)
    assert sizes[-1] == total - part_size * (len(sizes) - 1)
    full_parts = [part for part in yielded if len(part) == part_size]
    assert len({id(part) for part in full_parts}) == min(in_flight, len(full_parts))
    assert encryptor._free.empty()
