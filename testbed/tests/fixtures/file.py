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

from typing import Generator

from hexkit.providers.s3.testutils import FileObject, temp_file_object
from pytest import fixture

from src.config import Config

__all__ = ["file_fixture", "FileObject"]


@fixture
def file_fixture(config: Config) -> Generator[FileObject, None, None]:
    """File fixture that provides a temporary file."""

    with temp_file_object(
        bucket_id=config.staging_bucket,
        object_id=config.object_id,
        size=config.file_size,
    ) as temp_file:
        yield temp_file
