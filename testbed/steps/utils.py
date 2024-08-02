# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
from datetime import UTC, datetime
from pathlib import Path

from fixtures import Config, JointFixture
from fixtures.utils import calculate_checksum, write_data_to_yaml
from ghga_datasteward_kit.file_ingest import IngestConfig
from ghga_datasteward_kit.loading import LoadConfig
from hexkit.custom_types import JsonObject
from hexkit.providers.s3.testutils import FileObject
from pydantic import BaseModel, EmailStr

DATASET_OVERVIEW_KEYS = {"accession", "title", "description"}
FILE_OVERVIEW_KEYS = {
    "accession",
    "checksum",
    "checksum_type",
    "format",
    "name",
    "size",
}
EXPECTED_NOTIFICATIONS = {
    "access_request_created": "A data download access request has been created",
    "access_request_allowed": "Data download access has been allowed",
    "access_request_registered": "Your data download access request has been registered",
    "access_request_accepted": "Your data download access request has been accepted",
    "access_request_denied": "Your data download access request has been rejected",
    "account_details_changed": "Account Details Changed",
    "second_factor_recreated": "2FA Setup Recreated",
    "iva_code_requested": "IVA Request Received",
    "iva_verification_requested": "Contact Address Verification Request Received",
    "iva_code_transmitted": "Contact Address Verification Code Transmitted",
    "iva_code_submitted": "IVA Verification Code Submitted",
}


class Notification(BaseModel):
    """A container for email notification data."""

    id: str
    sender: EmailStr
    receiver: EmailStr
    created_time: datetime
    subject: str
    body_text: str

    def is_recent(self, seconds: int = 30) -> bool:
        """Check if the notification is recent"""
        return abs((datetime.now(UTC) - self.created_time).seconds) <= seconds


def ingest_config_as_file(config: IngestConfig):
    """Create upload config file for data steward kit files ingest-upload-metadata"""
    ingest_config = {
        "file_ingest_baseurl": config.file_ingest_baseurl,
        "file_ingest_pubkey": config.file_ingest_pubkey,
        "submission_store_dir": str(config.submission_store_dir),
        "input_dir": str(config.input_dir),
        "map_files_fields": config.map_files_fields,
        "selected_storage_alias": "test",
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
        "part_size": str(config.upload_part_size),
        "object_storages": {
            "test": {
                "bucket_id": config.staging_bucket,
                "credentials": {
                    "s3_access_key_id": config.s3_access_key_id,
                    "s3_secret_access_key": config.s3_secret_access_key.get_secret_value(),
                },
            }
        },
        "selected_storage_alias": "test",
        "output_dir": str(file_metadata_dir),
        "secret_ingest_baseurl": config.fis_url,
        "secret_ingest_pubkey": config.fis_pubkey,
    }
    if config.wkvs_url:
        upload_config["wkvs_api_url"] = config.wkvs_url

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
    alias: str | None = None,
) -> None:
    """Verify a file with given parameters"""
    file_path = target_dir
    name += extension
    if encrypted:
        name += ".c4gh"

    matching = [path for path in file_path.iterdir() if path.name == name]
    assert len(matching) == 1, f"File {name} was not found"

    if not encrypted:
        file_path = matching[0]

        if alias:
            # Note: We do not store or verify checksums for original files.
            # However, we still need to test that the correct files are downloaded.
            with open(file_path) as file:
                first_line = next(file).rstrip()
            # The first line containing file alias might be truncated by test file size.
            # Therefore, we check if it is a prefix of the alias.
            assert alias.startswith(first_line)


def search_dataset_rpc(
    fixtures: JointFixture,
    filters: list[dict[str, str]] | None = None,
    query: str | None = None,
    class_name: str = "EmbeddedDataset",
    limit: int | None = None,
    skip: int | None = None,
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


def parse_notifications(raw_data: dict) -> list[Notification]:
    """Parse Email data from Mailhog into a sorted list of Notification instances."""
    return [
        Notification(
            id=item["ID"],
            sender=item["Raw"]["From"],
            receiver=item["Raw"]["To"][0],
            created_time=datetime.fromisoformat(item["Created"]),
            subject=item["Content"]["Headers"]["Subject"][0],
            body_text=item["Content"]["Body"].split("--", 1)[0].strip(),
        )
        for item in sorted(raw_data["items"], key=lambda x: x["Created"], reverse=True)
    ]
