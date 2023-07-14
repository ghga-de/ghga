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

import subprocess  # nosec B404
from pathlib import Path

from hexkit.providers.s3.testutils import FileObject

from fixtures.config import Config
from steps.utils import upload_config_as_file

from .conftest import JointFixture, scenarios, set_state, then, when

scenarios("../features/12_upload_files.feature")


def call_data_steward_kit_upload(
    file_object: FileObject, config: Config, file_metadata_dir: Path
):
    """Call DSKit s3_upload command to upload temp_file to configured bucket"""

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
        timeout=10 * 60,
    )

    assert not completed_upload.stdout
    assert b"ERROR" not in completed_upload.stderr


@when("files are uploaded", target_fixture="file_objects")
def upload_files(fixtures: JointFixture, batch_file_fixture):
    file_metadata_dir = fixtures.submission.config.file_metadata_dir
    file_metadata_dir.mkdir(exist_ok=True)

    file_objects = batch_file_fixture
    for file_object in file_objects:
        call_data_steward_kit_upload(
            file_object=file_object,
            config=fixtures.config,
            file_metadata_dir=file_metadata_dir,
        )
    return file_objects


@then("metadata for each file exist")
def metadata_files_exist(fixtures: JointFixture, file_objects: list[FileObject]):
    file_metadata_dir = fixtures.submission.config.file_metadata_dir
    file_aliases = []
    for file_object in file_objects:
        metadata_file_path = file_metadata_dir / f"{file_object.object_id}.json"
        assert metadata_file_path.exists()
        file_aliases.append(file_object.object_id)
    set_state("we have file aliases", file_aliases, fixtures.mongo)
