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
from typing import Generator, Optional

from hexkit.providers.s3.testutils import FileObject
from pytest import fixture

from fixtures.config import Config
from fixtures.dsk import DskFixture
from steps.utils import get_ext_char

__all__ = ["FileObject", "batch_file_fixture"]


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


@fixture(name="batch_file_fixture")
def batch_file_fixture(config: Config, dsk: DskFixture) -> Generator[list, None, None]:
    """Batch file fixture that provides temporary files according to metadata."""

    temp_dir = Path(tempfile.gettempdir())
    metadata = json.loads(dsk.config.metadata_path.read_text())

    created_files = []
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

    yield created_files

    for file_object in created_files:
        os.remove(file_object.file_path)
