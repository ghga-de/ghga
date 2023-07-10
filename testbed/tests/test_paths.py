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

import subprocess  # nosec B404
import time
from datetime import timedelta

import httpx
import pytest
from ghga_datasteward_kit.file_ingest import IngestConfig, file_ingest
from ghga_service_commons.utils.utc_dates import now_as_utc

from src.utils import data_steward_upload_file, get_file_metadata_from_service
from tests.fixtures import (  # noqa: F401 # pylint: disable=unused-import
    JointFixture,
    auth_fixture,
    batch_create_file_fixture,
    config_fixture,
    file_fixture,
    joint_fixture,
    kafka_fixture,
    mongodb_fixture,
    s3_fixture,
    submission_config_fixture,
    submission_workdir,
)
from tests.fixtures.metadata import SubmissionConfig


@pytest.mark.asyncio
async def test_ars(fixtures: JointFixture):
    """Standalone test for the access request service.

    Checks that an access request can be made and notifications are sent out.
    """
    headers = fixtures.auth.generate_headers(
        id_="user-id-doe", name="John Doe", email="doe@home.org", title="Dr."
    )
    date_now = now_as_utc()
    data = {
        "user_id": "user-id-doe",
        "dataset_id": "some-dataset",
        "email": "john@doe.org",
        "request_text": "Can I access some dataset?",
        "access_starts": date_now.isoformat(),
        "access_ends": (date_now + timedelta(days=365)).isoformat(),
    }
    url = "http://ars:8080/access-requests"

    response = httpx.post(url, data=data)
    assert response.status_code == 403

    async with fixtures.kafka.record_events(in_topic="notifications") as event_recorder:
        response = httpx.post(url, headers=headers, json=data)
        assert response.status_code == 201

    assert (
        sum(
            1
            for event in event_recorder.recorded_events
            if event.type_ == "notification"
        )
        == 2
    )


@pytest.mark.asyncio
def test_upload_submission(
    workdir,
    submission_config: SubmissionConfig,
):
    """Test submission via DSKit with configured file object,
       expected to run through without errors

    This test case is not async at the moment because in submit workflow
    asyncio.run() is called by metldata dependency.
    """

    completed_submit = subprocess.run(  # nosec B607, B603
        [
            "ghga-datasteward-kit",
            "metadata",
            "submit",
            "--submission-title",
            "Test Submission",
            "--submission-description",
            "Test Submission Description",
            "--metadata-path",
            submission_config.metadata_path,
            "--config-path",
            submission_config.metadata_config_path,
        ],
        capture_output=True,
        check=True,
        timeout=10 * 60,
    )

    assert not completed_submit.stdout
    assert b"ERROR" not in completed_submit.stderr

    assert (workdir / submission_config.submission_store).exists()

    completed_transform = subprocess.run(  # nosec B607, B603
        [
            "ghga-datasteward-kit",
            "metadata",
            "transform",
            "--config-path",
            submission_config.metadata_config_path,
        ],
        capture_output=True,
        check=True,
        timeout=15 * 60,
    )

    assert not completed_transform.stdout
    assert b"ERROR" not in completed_transform.stderr


@pytest.mark.asyncio
async def test_upload_file_ingest(
    workdir,
    fixtures: JointFixture,
    batch_file_fixture,
    submission_config: SubmissionConfig,
):
    """Test DSkit DSKit file upload workflow"""

    file_objects = batch_file_fixture
    file_metadata_dir = workdir / "file_metadata"
    file_metadata_dir.mkdir()

    completed_submit = subprocess.run(  # nosec B607, B603
        [
            "ghga-datasteward-kit",
            "metadata",
            "submit",
            "--submission-title",
            "Test Submission",
            "--submission-description",
            "Test Submission Description",
            "--metadata-path",
            submission_config.metadata_path,
            "--config-path",
            submission_config.metadata_config_path,
        ],
        capture_output=True,
        check=True,
        timeout=10 * 60,
    )

    assert not completed_submit.stdout
    assert b"ERROR" not in completed_submit.stderr

    assert (workdir / submission_config.submission_store).exists()

    ingest_config = IngestConfig(
        file_ingest_url=fixtures.config.file_ingest_url,
        file_ingest_pubkey=fixtures.config.file_ingest_pubkey,
        input_dir=file_metadata_dir,
        submission_store_dir=workdir / submission_config.submission_store,
        map_files_fields=submission_config.metadata_file_fields,
    )

    for file_object in file_objects:
        completed_upload = data_steward_upload_file(
            file_object=file_object,
            config=fixtures.config,
            file_metadata_dir=file_metadata_dir,
        )

        assert not completed_upload.stdout
        assert b"ERROR" not in completed_upload.stderr

        metadata_file_path = file_metadata_dir / f"{file_object.object_id}.json"
        assert metadata_file_path.exists()

        file_ingest(
            in_path=metadata_file_path,
            token=fixtures.auth.read_token(),
            config=ingest_config,
        )

        # Wait for file copy and check IFRS database for metadata
        # also object storage for file
        time.sleep(10)
        db_metadata = get_file_metadata_from_service(
            ingest_config=ingest_config,
            db_connection_str=fixtures.config.db_connection_str,
            file_object=file_object,
            db_name="ifrs",
            collection_name="file_metadata",
        )

        assert db_metadata
        assert await fixtures.s3.storage.does_object_exist(
            bucket_id="permanent", object_id=db_metadata["object_id"]
        )
