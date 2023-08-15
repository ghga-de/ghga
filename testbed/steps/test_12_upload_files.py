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


""" Step definitions for file upload """

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Union

from hexkit.providers.s3.testutils import FileObject

from fixtures.config import Config
from steps.utils import upload_config_as_file

from .conftest import JointFixture, async_step, given, scenarios, set_state, then, when

scenarios("../features/12_upload_files.feature")


def call_data_steward_kit_upload(
    file_object: FileObject, config: Config, file_metadata_dir: Path
):
    """Call DSKit upload command to upload a file"""

    upload_config_path = upload_config_as_file(
        config=config, file_metadata_dir=file_metadata_dir
    )

    completed_upload = subprocess.run(  # nosec B607, B603
        [
            "ghga-datasteward-kit",
            "files",
            "upload",
            "--alias",
            file_object.object_id,
            "--input-path",
            str(file_object.file_path),
            "--config-path",
            upload_config_path,
        ],
        capture_output=True,
        check=True,
        encoding="utf-8",
        text=True,
        timeout=60,
    )

    assert not completed_upload.stdout
    assert "ERROR" not in completed_upload.stderr


def call_data_steward_kit_batch_upload(
    batch_files_tsv: str, config: Config, file_metadata_dir: Path
):
    """Call DSKit batch-upload command to upload listed files in TSV file"""

    upload_config_path = upload_config_as_file(
        config=config, file_metadata_dir=file_metadata_dir
    )

    completed_upload = subprocess.run(  # nosec B607, B603
        [
            "ghga-datasteward-kit",
            "files",
            "batch-upload",
            "--tsv",
            str(batch_files_tsv),
            "--config-path",
            upload_config_path,
            "--parallel-processes",
            "2",
        ],
        capture_output=True,
        check=True,
        encoding="utf-8",
        text=True,
        timeout=180,
    )

    assert not completed_upload.stdout
    assert "ERROR" not in completed_upload.stderr


@given("no files have been uploaded yet")
@async_step
async def upload_buckets_empty(fixtures: JointFixture):
    await fixtures.s3.empty_given_buckets(["staging"])


@given("no file metadata exists")
def local_metadata_empty(fixtures: JointFixture):
    file_metadata_dir = fixtures.dsk.config.file_metadata_dir
    if os.path.exists(file_metadata_dir):
        shutil.rmtree(file_metadata_dir)


@when("a single file is uploaded", target_fixture="uploaded_file")
def upload_single_file(fixtures: JointFixture, file_fixture):
    file_metadata_dir = fixtures.dsk.config.file_metadata_dir
    file_metadata_dir.mkdir(exist_ok=True)

    file_object = file_fixture
    call_data_steward_kit_upload(
        file_object=file_object,
        config=fixtures.config,
        file_metadata_dir=file_metadata_dir,
    )
    return file_object


@then(
    "the file metadata for the uploaded file exists",
    target_fixture="uploaded_file_uuids",
)
def metadata_file_exist(fixtures: JointFixture, uploaded_file: FileObject):
    """Check the metadata for the uploaded file exists
    Return the file uuid to be used as object storage id"""
    file_metadata_dir = fixtures.dsk.config.file_metadata_dir
    metadata_file_path = file_metadata_dir / f"{uploaded_file.object_id}.json"
    assert metadata_file_path.exists()

    file_uuid = json.loads(metadata_file_path.read_text())["File UUID"]
    return file_uuid


@then("the uploaded file exists in the staging bucket")
@then("the uploaded files exist in the staging bucket")
@async_step
async def check_file_in_storage(
    fixtures: JointFixture, uploaded_file_uuids: Union[str, list]
):
    """Check object exist with async fixture"""
    if isinstance(uploaded_file_uuids, str):
        uploaded_file_uuids = [uploaded_file_uuids]
    for uploaded_file_uuid in uploaded_file_uuids:
        assert await fixtures.s3.storage.does_object_exist(
            bucket_id=fixtures.config.staging_bucket, object_id=uploaded_file_uuid
        )


@when("multiple files are uploaded as a batch", target_fixture="file_objects")
def upload_files(fixtures: JointFixture, batch_file_fixture):
    file_metadata_dir = fixtures.dsk.config.file_metadata_dir
    file_metadata_dir.mkdir(exist_ok=True)

    tsv_file = batch_file_fixture.tsv_file
    call_data_steward_kit_batch_upload(
        batch_files_tsv=tsv_file,
        config=fixtures.config,
        file_metadata_dir=file_metadata_dir,
    )
    return batch_file_fixture.file_objects


@then(
    "the file metadata for each uploaded file exists",
    target_fixture="uploaded_file_uuids",
)
def metadata_files_exist(fixtures: JointFixture, file_objects: list[FileObject]):
    """Check the metadata for each uploaded file exists
    Set the state and save file aliases
    """
    file_metadata_dir = fixtures.dsk.config.file_metadata_dir
    file_aliases, file_uuids = [], []
    for file_object in file_objects:
        metadata_file_path = file_metadata_dir / f"{file_object.object_id}.json"
        assert metadata_file_path.exists()
        file_aliases.append(file_object.object_id)
        file_uuid = json.loads(metadata_file_path.read_text())["File UUID"]
        file_uuids.append(file_uuid)

    set_state("we have file aliases", file_aliases, fixtures.mongo)
    return file_uuids
