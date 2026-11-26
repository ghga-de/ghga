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

"""Integration tests for run_dhfs_verification setup and teardown.

Most tests mock the core interrogation logic (prepare_interrogator /
interrogate_new_files) to focus on inbox upload and cleanup behavior; one runs the
real interrogator.
"""

import hashlib
import io
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from math import ceil
from unittest.mock import AsyncMock, MagicMock, patch

import crypt4gh.lib
import httpx2
import pytest
import pytest_asyncio

from dhfs.adapters.outbound.central import CentralClient
from dhfs.adapters.outbound.s3 import S3Client
from dhfs.config import Config
from dhfs.core.verifier import (
    INTERROGATION_OBJECT_ID,
    OBJECT_ID_STR,
    OBJECT_ID_UUID,
    _upload_inbox_dummy_file,
    run_dhfs_verification,
)
from hexkit.providers.s3.testutils import S3Fixture
from tests.fixtures.utils import (
    DHFS_CRYPT4GH_PUBLIC_KEY_PATH,
    get_crypt4gh_private_key,
)

pytestmark = pytest.mark.asyncio

INBOX_BUCKET_ID = "verifier-test-inbox"
SMALL_FILE_SIZE = 1 * 1024**2  # 1 MiB — keeps tests fast


@dataclass
class VerifierFixture:
    """Bundles Verifier Config with the S3 fixture."""

    config: Config
    s3: S3Fixture


@pytest_asyncio.fixture
async def verifier_fixture(
    s3: S3Fixture, config: Config
) -> AsyncGenerator[VerifierFixture]:
    """Extends the base Config with verifier-specific settings and creates both buckets.

    The version check via Central API (fetch_new_uploads) is mocked.
    """
    patched = config.model_dump()
    patched.update(s3.config.model_dump())
    patched.update(
        {
            "inbox_bucket_id": INBOX_BUCKET_ID,
            "inbox_write_s3_access_key_id": s3.config.s3_access_key_id,
            "inbox_write_s3_secret_access_key": s3.config.s3_secret_access_key,
            "data_hub_crypt4gh_public_key_path": DHFS_CRYPT4GH_PUBLIC_KEY_PATH,
        }
    )
    verifier_config = Config(**patched)

    await s3.storage.create_bucket(INBOX_BUCKET_ID)
    await s3.storage.create_bucket(verifier_config.interrogation_bucket_id)

    with patch.object(CentralClient, "fetch_new_uploads", AsyncMock(return_value=[])):
        yield VerifierFixture(config=verifier_config, s3=s3)


@asynccontextmanager
async def _succeeding_interrogator(*, config):
    """Drop-in for prepare_interrogator that simulates a successful interrogation,
    reported to Central the way the real one reports it.
    """

    async def interrogate_new_files():
        await CentralClient.submit_interrogation_report(
            MagicMock(), report=MagicMock(passed=True)
        )

    mock = AsyncMock()
    mock.interrogate_new_files.side_effect = interrogate_new_files
    yield mock


@asynccontextmanager
async def _failing_interrogator(*, config):
    """Drop-in for prepare_interrogator that simulates a failed interrogation."""
    mock = AsyncMock()
    mock.interrogate_new_files.side_effect = RuntimeError("Simulated failure")
    yield mock


async def _inbox_has_object(fixture: VerifierFixture) -> bool:
    return await fixture.s3.storage.does_object_exist(
        bucket_id=INBOX_BUCKET_ID, object_id=str(OBJECT_ID_UUID)
    )


async def test_fresh_run_cleans_up_on_success(verifier_fixture: VerifierFixture):
    """Verify that a successful run uploads the dummy file, interrogates (mocked), then
    removes the inbox object.
    """
    with patch("dhfs.core.verifier.prepare_interrogator", _succeeding_interrogator):
        await run_dhfs_verification(verifier_fixture.config, file_size=SMALL_FILE_SIZE)

    assert not await _inbox_has_object(verifier_fixture), (
        "Inbox dummy object should be removed after a successful run"
    )


async def test_real_interrogator_processes_the_dummy_file(
    verifier_fixture: VerifierFixture, caplog: pytest.LogCaptureFixture
):
    """Verify that the dummy file passes the real interrogator and that its report
    reaches the verifier the way a real file's report reaches Central.
    """
    with caplog.at_level(logging.INFO, logger="dhfs.core.verifier"):
        await run_dhfs_verification(verifier_fixture.config, file_size=SMALL_FILE_SIZE)

    # A failed setup is only logged, so success has to be read from the log
    assert "File processing succeeded." in caplog.messages
    assert not await _inbox_has_object(verifier_fixture)
    assert not await verifier_fixture.s3.storage.does_object_exist(
        bucket_id=verifier_fixture.config.interrogation_bucket_id,
        object_id=str(INTERROGATION_OBJECT_ID),
    )


async def test_inconclusive_run_names_the_cause(verifier_fixture: VerifierFixture):
    """An inconclusive attempt of the real interrogator must fail the verification
    with the cause DHFS found, not only log it.
    """
    with (
        patch.object(S3Client, "get_is_file_in_inbox", AsyncMock(return_value=False)),
        pytest.raises(RuntimeError, match="was not found in the inbox"),
    ):
        await run_dhfs_verification(verifier_fixture.config, file_size=SMALL_FILE_SIZE)

    assert not await _inbox_has_object(verifier_fixture)


async def test_failure_cleans_up(verifier_fixture: VerifierFixture):
    """Verify that the inbox object is removed during cleanup when interrogation fails."""
    with pytest.raises(RuntimeError, match="Simulated failure"):
        with patch("dhfs.core.verifier.prepare_interrogator", _failing_interrogator):
            await run_dhfs_verification(
                verifier_fixture.config, file_size=SMALL_FILE_SIZE
            )

    assert not await _inbox_has_object(verifier_fixture), (
        "Inbox object should be removed even when interrogation fails"
    )


async def test_dummy_file_is_uploaded_in_parts(verifier_fixture: VerifierFixture):
    """The dummy file must arrive in parts of the given size and decrypt to plaintext
    of the stated size and checksum.
    """
    part_size = 5 * 1024**2  # the smallest part S3 accepts before the last one
    file_size = 2 * part_size + 12345

    file_upload = await _upload_inbox_dummy_file(
        config=verifier_fixture.config,
        inbox_write_storage=verifier_fixture.s3.storage,
        public_key_path=DHFS_CRYPT4GH_PUBLIC_KEY_PATH,
        file_size=file_size,
        part_size=part_size,
    )

    assert file_upload.part_size == part_size
    storage = verifier_fixture.s3.storage
    # A multipart ETag ends in the part count
    etag = await storage.get_object_etag(
        bucket_id=INBOX_BUCKET_ID, object_id=OBJECT_ID_STR
    )
    part_count = ceil(file_upload.encrypted_size / part_size)
    assert etag.strip('"').endswith(f"-{part_count}")
    url = await storage.get_object_download_url(
        bucket_id=INBOX_BUCKET_ID, object_id=OBJECT_ID_STR
    )
    encrypted = httpx2.get(url).content
    assert len(encrypted) == file_upload.encrypted_size

    plaintext = io.BytesIO()
    keys = [(0, get_crypt4gh_private_key().get_secret_value(), None)]
    crypt4gh.lib.decrypt(keys, io.BytesIO(encrypted), plaintext)
    assert len(plaintext.getvalue()) == file_upload.decrypted_size == file_size
    assert (
        hashlib.sha256(plaintext.getvalue()).hexdigest() == file_upload.decrypted_sha256
    )
