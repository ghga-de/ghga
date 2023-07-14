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

""" Utilities for tests """

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import yaml
from ghga_datasteward_kit.file_ingest import IngestConfig

from fixtures.config import Config


@contextmanager
def temporary_file(file_path, content):
    """Yield the temporary file with required content"""
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
        yield file_path
    finally:
        os.remove(file_path)


def write_data_to_yaml(data: dict[str, str], file_path=None):
    if not file_path:
        _, file_path = tempfile.mkstemp()  # pylint: disable=consider-using-with

    with open(file_path, "w", encoding="utf-8") as _file:
        yaml.dump(data, _file)

    return file_path


def ingest_config_as_file(config: IngestConfig):
    """Create upload config file for data steward s3_upload"""

    ingest_config = {
        "file_ingest_url": config.file_ingest_url,
        "file_ingest_pubkey": config.file_ingest_pubkey,
        "submission_store_dir": str(config.submission_store_dir),
        "input_dir": str(config.input_dir),
        "map_files_fields": config.map_files_fields,
    }

    return write_data_to_yaml(data=ingest_config)


def upload_config_as_file(config: Config, file_metadata_dir: Path):
    """Create upload config file for data steward s3_upload"""

    upload_config = {
        "s3_endpoint_url": config.s3_endpoint_url,
        "s3_access_key_id": config.s3_access_key_id,
        "s3_secret_access_key": config.s3_secret_access_key.get_secret_value(),
        "bucket_id": config.staging_bucket,
        "part_size": str(config.part_size),
        "output_dir": str(file_metadata_dir),
    }

    return write_data_to_yaml(data=upload_config)


def get_ext_char(file_path: Path):
    """Get file path and return first character of the extension"""
    first_char = " "
    if file_path.suffixes:
        first_char = file_path.suffixes[0].strip(".")[0]
    return first_char
