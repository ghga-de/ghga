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

import subprocess  # nosec B404
import tempfile
from pathlib import Path

import yaml
from ghga_datasteward_kit.file_ingest import IngestConfig, alias_to_accession
from hexkit.providers.s3.testutils import FileObject
from metldata.submission_registry.submission_store import SubmissionStore
from pydantic import SecretStr

from src.config import Config
from tests.fixtures.mongodb import retrieve_document_from_service_db


def upload_config_path_fixture(config: Config, file_metadata_dir: Path):
    """Create upload config file for data steward s3_upload"""

    upload_config = {
        "s3_endpoint_url": config.s3_endpoint_url,
        "s3_access_key_id": config.s3_access_key_id,
        "s3_secret_access_key": config.s3_secret_access_key.get_secret_value(),
        "bucket_id": config.staging_bucket,
        "part_size": 1024,
        "output_dir": str(file_metadata_dir),
    }

    _, temp_file_path = tempfile.mkstemp()  # pylint: disable=consider-using-with
    with open(temp_file_path, "w", encoding="utf-8") as _file:
        yaml.dump(upload_config, _file)

    return temp_file_path


def data_steward_upload_file(
    file_object: FileObject, config: Config, file_metadata_dir: Path
):
    """Call DSKit s3_upload command to upload temp_file to configured bucket"""

    upload_config_path = upload_config_path_fixture(
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

    return completed_upload


def get_file_metadata_from_service(
    file_object: FileObject,
    ingest_config: IngestConfig,
    db_connection_str: SecretStr,
    db_name: str,
    collection_name: str,
):
    """
    - First get file accession from submission_store
    - Then get file metadata from service database using accession
    - Finally check object storage if file exists
    """
    submission_store = SubmissionStore(config=ingest_config)

    accession = alias_to_accession(
        alias=file_object.object_id,
        map_fields=ingest_config.map_files_fields,
        submission_store=submission_store,
    )
    return retrieve_document_from_service_db(
        db_connection_str=db_connection_str,
        db_name=db_name,
        collection_name=collection_name,
        query={"_id": accession},
    )
