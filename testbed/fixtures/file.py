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
from typing import Generator, List, Optional

from hexkit.providers.s3.testutils import FileObject, temp_file_object
from pydantic import BaseModel
from pytest import fixture

from fixtures.config import Config
from fixtures.dsk import DskFixture
from steps.utils import get_ext_char

__all__ = ["FileObject", "batch_file_fixture", "file_fixture"]


class FileBatch(BaseModel):
    """File batch model"""

    file_objects: List[FileObject]
    tsv_file: Path


def create_named_file(
    target_dir: Path,
    config: Config,
    name: str,
    file_size: Optional[int] = None,
    alias: Optional[str] = None,
) -> FileObject:
    """Create a file with given parameters"""
    file_path = target_dir / name

    file_size = config.file_size if not file_size else file_size
    alias = os.path.splitext(name)[0] if not alias else alias

    with open(file_path, "w", encoding="utf-8") as file:
        content_char = get_ext_char(Path(file_path))
        file_content = content_char * file_size
        file.write(file_content)

    file_object = FileObject(
        file_path=Path(file_path),
        bucket_id=config.staging_bucket,
        object_id=alias,
    )
    return file_object


@fixture(name="file_fixture")
def file_fixture(config: Config) -> Generator[FileObject, None, None]:
    """File fixture that provides a temporary file."""

    with temp_file_object(
        bucket_id=config.staging_bucket,
        object_id=config.object_id,
        size=config.file_size,
    ) as temp_file:
        yield temp_file


@fixture(name="batch_file_fixture")
def batch_file_fixture(
    config: Config, dsk: DskFixture
) -> Generator[FileBatch, None, None]:
    """Batch file fixture that provides temporary files according to metadata."""

    temp_dir = Path(tempfile.gettempdir())
    metadata = json.loads(dsk.config.complete_metadata_path.read_text())

    created_files = []
    with open(dsk.config.files_to_upload_tsv, "w", encoding="utf-8") as tsv_file:
        for file_field in dsk.config.metadata_file_fields:
            files = metadata[file_field]
            for file_ in files:
                file_object = create_named_file(
                    target_dir=temp_dir,
                    config=config,
                    name=file_["name"],
                    file_size=file_["size"],
                    alias=file_["alias"],
                )

                created_files.append(file_object)
                tsv_file.write(f"{file_object.file_path}\t{file_object.object_id}\n")

    file_batch = FileBatch(
        file_objects=created_files, tsv_file=dsk.config.files_to_upload_tsv
    )

    yield file_batch

    for file_object in file_batch.file_objects:
        os.remove(file_object.file_path)
