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

"""Fixture for testing code that uses the FileObject provider."""

import json
import os
import tempfile
from pathlib import Path
from typing import Generator

from hexkit.providers.s3.testutils import FileObject, temp_file_object
from pytest import fixture

from fixtures.config import Config
from fixtures.metadata import SubmissionConfig

__all__ = ["file_fixture", "FileObject", "batch_create_file_fixture"]


def create_named_file(target_dir: str, config: Config, name: str) -> FileObject:
    """Create a file with given parameters"""
    file_path = os.path.join(target_dir, name)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(" " * config.file_size)

    file_object = FileObject(
        file_path=Path(file_path),
        bucket_id=config.staging_bucket,
        object_id=name.split(".")[0],
    )
    return file_object


@fixture(name="temp_file_fixture")
def file_fixture(config: Config) -> Generator[FileObject, None, None]:
    """File fixture that provides a temporary file."""

    with temp_file_object(
        bucket_id=config.staging_bucket,
        object_id=config.object_id,
        size=config.file_size,
    ) as temp_file:
        yield temp_file


@fixture(name="batch_file_fixture")
def batch_create_file_fixture(
    config: Config, submission_config: SubmissionConfig
) -> Generator[list, None, None]:
    """Batch file fixture that provides temporary files according to metadata."""

    temp_dir = tempfile.gettempdir()
    metadata = json.loads(submission_config.metadata_path.read_text())

    created_files = []
    for file_field in submission_config.metadata_file_fields:
        files = metadata[file_field]

        for _file in files:
            file_object = create_named_file(
                target_dir=temp_dir, config=config, name=_file["name"]
            )

            created_files.append(file_object)

    yield created_files

    for file_object in created_files:
        os.remove(file_object.file_path)
