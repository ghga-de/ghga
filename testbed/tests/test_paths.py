# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A test dummy just to make the CI pass."""

import time
from pathlib import Path

import pytest
from ghga_connector.cli import config
from ghga_connector.core.api_calls import get_file_metadata, get_upload_info
from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.providers.akafka.testutils import (
    EventRecorder,
    ExpectedEvent,
    check_recorded_events,
)

from src.commons import CONFIG
from src.download_path import decrypt_file, download_file
from src.upload_path import delegate_paths


@pytest.mark.asyncio
async def test_full_path(tmp_path):
    """Test up- and download path"""
    unencrypted_id, encrypted_id, unencrypted_data, checksum = await delegate_paths()

    await check_upload_path(unencrypted_id=unencrypted_id, encrypted_id=encrypted_id)
    await check_download_path(
        encrypted_id=encrypted_id, checksum=checksum, output_dir=tmp_path
    )
    decrypt_and_check(
        encrypted_id=encrypted_id, content=unencrypted_data, tmp_dir=tmp_path
    )


async def check_upload_path(*, unencrypted_id: str, encrypted_id: str):
    """Check correct state for upload path"""
    await check_upload_status(file_id=unencrypted_id, expected_status="rejected")
    # <= 180 did not work in actions, so let's currently keep it this way
    time.sleep(240)
    await check_upload_status(file_id=encrypted_id, expected_status="accepted")


async def check_upload_status(*, file_id: str, expected_status: str):
    """Assert upload attempt state matches expected state"""
    metadata = get_file_metadata(api_url=config.upload_api, file_id=file_id)
    upload_id = metadata["latest_upload_id"]
    upload_attempt = get_upload_info(api_url=config.upload_api, upload_id=upload_id)
    assert upload_attempt["status"] == expected_status


async def check_download_path(*, encrypted_id: str, checksum: str, output_dir: Path):
    """Check correct state for download path"""

    # record download_served event
    event_recorder = EventRecorder(
        kafka_servers=CONFIG.kafka_servers, topic="file_downloads"
    )
    async with event_recorder:
        download_file(file_id=encrypted_id, output_dir=output_dir)

    # construct expected event
    payload = event_schemas.FileDownloadServed(
        file_id=encrypted_id, decrypted_sha256=checksum, context="unknown"
    ).dict()
    type_ = "download_served"
    key = encrypted_id
    expected_event = ExpectedEvent(payload=payload, type_=type_, key=key)

    # filter for relevant event type
    recorded_events = [
        event for event in event_recorder.recorded_events if event.type_ == type_
    ]

    check_recorded_events(
        recorded_events=recorded_events,
        expected_events=[expected_event, expected_event],
    )


def decrypt_and_check(encrypted_id: str, content: bytes, tmp_dir: Path):
    """Decrypt file and compare to original"""

    encrypted_location = tmp_dir / encrypted_id
    decrypted_location = tmp_dir / f"{encrypted_id}_decrypted"

    decrypt_file(input_location=encrypted_location, output_location=decrypted_location)

    with decrypted_location.open("rb") as dl_file:
        downloaded_content = dl_file.read()

    # cleanup
    encrypted_location.unlink()
    decrypted_location.unlink()

    assert downloaded_content == content
