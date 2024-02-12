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

"""Utilities used in step functions"""

import json
from pathlib import Path
from typing import Optional

from fixtures import Config, JointFixture
from fixtures.utils import calculate_checksum, write_data_to_yaml
from ghga_datasteward_kit.file_ingest import IngestConfig
from ghga_datasteward_kit.loading import LoadConfig
from hexkit.custom_types import JsonObject
from hexkit.providers.s3.testutils import FileObject

DATASET_OVERVIEW_KEYS = {"accession", "title", "description"}
FILE_OVERVIEW_KEYS = {
    "accession",
    "checksum",
    "checksum_type",
    "format",
    "name",
    "size",
}


def ingest_config_as_file(config: IngestConfig):
    """Create upload config file for data steward kit files ingest-upload-metadata"""
    ingest_config = {
        "file_ingest_baseurl": config.file_ingest_baseurl,
        "file_ingest_pubkey": config.file_ingest_pubkey,
        "submission_store_dir": str(config.submission_store_dir),
        "input_dir": str(config.input_dir),
        "map_files_fields": config.map_files_fields,
    }

    return write_data_to_yaml(data=ingest_config)


def load_config_as_file(config: LoadConfig):
    """Create upload config file for data steward kit files load"""
    load_config = {
        "event_store_path": str(config.event_store_path),
        "artifact_topic_prefix": config.artifact_topic_prefix,
        "artifact_types": config.artifact_types,
        "loader_api_root": config.loader_api_root,
    }

    return write_data_to_yaml(data=load_config)


def upload_config_as_file(config: Config, file_metadata_dir: Path):
    """Create upload config file for data steward kit files upload"""
    upload_config = {
        "s3_endpoint_url": config.s3_endpoint_url,
        "s3_access_key_id": config.s3_access_key_id,
        "s3_secret_access_key": config.s3_secret_access_key.get_secret_value(),
        "bucket_id": config.staging_bucket,
        "part_size": str(config.upload_part_size),
        "output_dir": str(file_metadata_dir),
        "secret_ingest_baseurl": config.fis_url,
        "secret_ingest_pubkey": config.fis_pubkey,
    }

    return write_data_to_yaml(data=upload_config)


def get_ext_char(file_path: Path):
    """Get file path and return first character of the extension"""
    first_char = " "
    if file_path.suffixes:
        first_char = file_path.suffixes[0].strip(".")[0]
    return first_char


def verify_named_file(
    target_dir: Path,
    name: str,
    extension: str,
    encrypted=False,
    checksum: Optional[str] = None,
    size_in_bytes: Optional[int] = None,
) -> None:
    """Verify a file with given parameters"""
    file_path = target_dir
    name += extension
    if encrypted:
        name += ".c4gh"

    matching = [path for path in file_path.iterdir() if path.name == name]
    assert len(matching) == 1, f"File {name} was not found"

    if not encrypted:
        if size_in_bytes is None:
            raise ValueError("size_in_bytes must be provided for non-encrypted files")

        if checksum is None:
            raise ValueError("checksum must be provided for non-encrypted files")

        file_path = matching[0]

        file_size_in_bytes = file_path.stat().st_size
        assert file_size_in_bytes == size_in_bytes

        with open(file_path, "rb") as file:
            file_checksum = calculate_checksum(file.read())
        assert file_checksum == checksum


def search_dataset_rpc(
    fixtures: JointFixture,
    filters: Optional[list[dict[str, str]]] = None,
    query: Optional[str] = None,
    class_name: str = "EmbeddedDataset",
    limit: Optional[int] = None,
    skip: Optional[int] = None,
):
    """Send a search request to the metadata artifact search service."""
    search_parameters: JsonObject = {
        "class_name": class_name,
        **{
            key: value
            for key, value in {
                "limit": limit,
                "query": query,
                "skip": skip,
                "filters": filters,
            }.items()
            if value is not None
        },
    }
    url = f"{fixtures.config.mass_url}/rpc/search"
    return fixtures.http.post(url, json=search_parameters)


def get_dataset_overview(content: dict) -> dict:
    """Condense a dataset content dict to a dataset overview dict."""
    simplified = {}
    files = {}
    for key, value in content.items():
        if key in DATASET_OVERVIEW_KEYS:
            simplified[key] = value
        elif key.endswith("_files"):
            for file_ in value:
                alias = file_.pop("alias")
                files[alias] = {
                    key: value
                    for key, value in file_.items()
                    if key in FILE_OVERVIEW_KEYS
                }
    simplified["files"] = files
    return simplified


def get_secret_ids(file_metadata_dir: Path, file_objects: list[FileObject]) -> set[str]:
    """Returns secret ids of the ingested files using their file metadata"""
    secret_ids = set()
    for file_object in file_objects:
        metadata_file_path = file_metadata_dir / f"{file_object.object_id}.json"
        secret_id = json.loads(metadata_file_path.read_text())[
            "Symmetric file encryption secret ID"
        ]
        secret_ids.add(secret_id)
    return secret_ids
