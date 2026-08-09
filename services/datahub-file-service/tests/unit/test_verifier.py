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

"""Unit tests for the check (verifier) setup/teardown logic."""

import logging
from functools import partial
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dhfs.adapters.outbound.central import UPLOADS_PATH
from dhfs.config import Config
from dhfs.core.verifier import (
    INTERROGATION_OBJECT_ID,
    OBJECT_ID_STR,
    _clean_buckets,
    _upload_inbox_dummy_file,
    _validate_config_for_verifier,
    run_dhfs_verification,
)
from tests.fixtures.central_api import CentralApiMock, get_mocked_httpx_client


@pytest.mark.parametrize(
    "missing_field",
    [
        "inbox_bucket_id",
        "data_hub_crypt4gh_public_key_path",
        "inbox_write_s3_access_key_id",
        "inbox_write_s3_secret_access_key",
    ],
)
def test_validate_config_requires_each_field(missing_field: str):
    """Verify that each optional config field the check depends on must be set."""
    config = MagicMock()
    setattr(config, missing_field, None)
    with pytest.raises(ValueError, match=missing_field):
        _validate_config_for_verifier(config)


@pytest.mark.parametrize(
    "inbox_exists, interrogation_exists, missing_bucket",
    [(False, True, "my-inbox"), (True, False, "my-interrogation")],
)
@pytest.mark.asyncio
async def test_run_dhfs_verification_raises_when_required_bucket_missing(
    inbox_exists: bool, interrogation_exists: bool, missing_bucket: str
):
    """Verify that run_dhfs_verification aborts with a ValueError naming whichever required bucket is
    missing.
    """
    config = MagicMock()
    config.inbox_bucket_id = "my-inbox"
    config.interrogation_bucket_id = "my-interrogation"

    inbox_write_storage = AsyncMock()
    inbox_write_storage.does_bucket_exist.return_value = inbox_exists
    dhfs_storage = AsyncMock()
    dhfs_storage.does_bucket_exist.return_value = interrogation_exists

    with (
        patch(
            "dhfs.core.verifier._get_inbox_storage_with_write_access",
            return_value=inbox_write_storage,
        ),
        patch("dhfs.core.verifier.S3ObjectStorage", return_value=dhfs_storage),
    ):
        with pytest.raises(ValueError, match=missing_bucket):
            await run_dhfs_verification(config, file_size=1024)


@pytest.mark.asyncio
async def test_run_dhfs_verification_pings_central_new_uploads_endpoint(config: Config):
    """Make sure that verification pings Central's 'new uploads' endpoint to confirm
    the DHFS version is good to go.
    """
    verifier_config = config.model_copy(
        update={
            "inbox_bucket_id": "inbox",
            "inbox_write_s3_access_key_id": "key",
            "inbox_write_s3_secret_access_key": "secret",
            "data_hub_crypt4gh_public_key_path": Path("/fake/key.pub"),
        }
    )
    base_url = str(verifier_config.central_api_url).rstrip("/")
    expected_url = base_url + UPLOADS_PATH.format(
        storage_alias=verifier_config.storage_alias
    )
    central_api = CentralApiMock(config=verifier_config)

    storage = AsyncMock()
    storage.does_bucket_exist.return_value = True

    # Skip everything after the ping, only testing the Central API call
    with (
        patch(
            "dhfs.core.verifier._get_inbox_storage_with_write_access",
            return_value=storage,
        ),
        patch("dhfs.core.verifier.S3ObjectStorage", return_value=storage),
        patch(
            "dhfs.core.verifier._clean_buckets",
            new=AsyncMock(side_effect=RuntimeError),
        ),
        patch(
            "dhfs.core.verifier.get_configured_httpx_client",
            partial(get_mocked_httpx_client, central_api=central_api),
        ),
    ):
        await run_dhfs_verification(verifier_config, file_size=1024)

    assert [(request.method, str(request.url)) for request in central_api.requests] == [
        ("GET", expected_url)
    ]


@pytest.mark.asyncio
async def test_clean_buckets():
    """Verify that cleanup targets the right bucket/object IDs using the right storage
    objects (which have different permissions).
    """
    config = MagicMock()
    config.inbox_bucket_id = "inbox"
    config.interrogation_bucket_id = "interrogation"

    inbox_write_storage = AsyncMock()
    inbox_write_storage.list_multipart_uploads_for_object.return_value = ["lingering"]
    dhfs_storage = AsyncMock()
    dhfs_storage.list_multipart_uploads_for_object.return_value = []

    await _clean_buckets(
        config=config,
        inbox_write_storage=inbox_write_storage,
        dhfs_storage=dhfs_storage,
    )

    inbox_write_storage.abort_multipart_upload.assert_awaited_once_with(
        upload_id="lingering", bucket_id="inbox", object_id=OBJECT_ID_STR
    )
    inbox_write_storage.delete_object.assert_awaited_once_with(
        bucket_id="inbox", object_id=OBJECT_ID_STR
    )
    dhfs_storage.delete_object.assert_awaited_once_with(
        bucket_id="interrogation", object_id=str(INTERROGATION_OBJECT_ID)
    )


@pytest.mark.asyncio
async def test_clean_buckets_wraps_unexpected_errors_with_bucket_name():
    """Verify that an unexpected storage error is re-raised as a RuntimeError naming the
    bucket.
    """
    config = MagicMock()
    config.inbox_bucket_id = "inbox"
    config.interrogation_bucket_id = "interrogation"

    failing_storage = AsyncMock()
    failing_storage.list_multipart_uploads_for_object.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError, match="inbox"):
        await _clean_buckets(
            config=config,
            inbox_write_storage=failing_storage,
            dhfs_storage=AsyncMock(),
        )


@pytest.mark.asyncio
async def test_upload_inbox_dummy_file_error(caplog):
    """Verify that a failed inbox upload re-raises as RuntimeError."""
    config = MagicMock()
    config.storage_alias = "test-hub"
    config.inbox_bucket_id = "test-inbox"

    encrypted_object = MagicMock()
    encrypted_object.checksums.unencrypted_sha256.hexdigest.return_value = "a" * 64
    encrypted_object.unencrypted_size = 10
    encrypted_object.encrypted_size = 20
    encrypted_object.part_size = 5

    with (
        patch(
            "dhfs.core.verifier._generate_encrypted_object",
            return_value=encrypted_object,
        ),
        patch(
            "dhfs.core.verifier._upload_encrypted_object",
            new=AsyncMock(side_effect=RuntimeError("denied")),
        ),
        caplog.at_level(logging.ERROR, logger="dhfs.core.verifier"),
    ):
        with pytest.raises(RuntimeError, match="Failed to upload the dummy file"):
            await _upload_inbox_dummy_file(
                config=config,
                inbox_write_storage=AsyncMock(),
                public_key_path=Path("/fake/key.pub"),
                file_size=1024,
            )
