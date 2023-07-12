# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
#


""" Step definitions for file ingest tests """

import subprocess  # nosec B404
import time

import pytest
from ghga_datasteward_kit.file_ingest import IngestConfig

from fixtures.metadata import SubmissionConfig
from steps.utils import (
    data_steward_upload_file,
    file_ingest,
    get_file_metadata_from_service,
)

from .conftest import JointFixture


@pytest.mark.asyncio
async def test_file_ingest(
    submission_workdir,
    fixtures: JointFixture,
    batch_file_fixture,
    submission_config: SubmissionConfig,
):
    """Test DSkit DSKit file upload workflow"""

    file_objects = batch_file_fixture
    file_metadata_dir = submission_workdir / "file_metadata"
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

    assert (submission_workdir / submission_config.submission_store).exists()

    ingest_config = IngestConfig(
        file_ingest_url=fixtures.config.file_ingest_url,
        file_ingest_pubkey=fixtures.config.file_ingest_pubkey,
        input_dir=file_metadata_dir,
        submission_store_dir=submission_workdir / submission_config.submission_store,
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

        completed_ingest = file_ingest(
            token=fixtures.auth.read_simple_token(),
            config=ingest_config,
        )

        assert not completed_ingest.returncode
        assert b"ERROR" not in completed_ingest.stderr

        # Wait for file copy and check IFRS database for metadata
        # also object storage for file
        time.sleep(10)
        db_metadata = get_file_metadata_from_service(
            ingest_config=ingest_config,
            file_object=file_object,
            db_name="ifrs",
            collection_name="file_metadata",
            mongo=fixtures.mongo,
        )

        assert db_metadata
        assert await fixtures.s3.storage.does_object_exist(
            bucket_id="permanent", object_id=db_metadata["object_id"]
        )
