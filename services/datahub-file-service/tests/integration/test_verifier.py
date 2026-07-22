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

The core interrogation logic (prepare_interrogator / interrogate_file) is mocked
so these tests focus exclusively on inbox upload and cleanup behavior.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from hexkit.providers.s3.testutils import S3Fixture

from dhfs.adapters.outbound.central import CentralClient
from dhfs.config import Config
from dhfs.core.verifier import OBJECT_ID_UUID, run_dhfs_verification
from tests.fixtures.utils import DHFS_CRYPT4GH_PUBLIC_KEY_PATH

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
    """Drop-in for prepare_interrogator that simulates a successful interrogation."""
    yield AsyncMock()


@asynccontextmanager
async def _failing_interrogator(*, config):
    """Drop-in for prepare_interrogator that simulates a failed interrogation."""
    mock = AsyncMock()
    mock.interrogate_file.side_effect = RuntimeError("Simulated failure")
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
