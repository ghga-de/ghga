# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""General testing utilities"""

from pathlib import Path
from uuid import UUID, uuid4

import ghga_event_schemas.pydantic_ as event_schemas
from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4

from dins.core import models

BASE_DIR = Path(__file__).parent.resolve()

FILE_ID_1 = UUID("6157d248-4baa-4f86-b1b9-b5476a55c12a")
FILE_ID_2 = UUID("753d3b20-eb18-4379-9874-1171cfa24831")
FILE_ID_3 = UUID("8eba8ab1-6e86-4d65-9c45-1586f73950fa")
ACCESSION1 = "GHGA001"
ACCESSION2 = "GHGA002"
ACCESSION3 = "GHGA003"
DECRYPTED_SHA256 = "fake-checksum"
DECRYPTED_SIZE = 12345678


def make_file_internally_registered(
    file_id: UUID4 | None = None,
    storage_alias: str = "HD01",
    decrypted_sha256: str = "a1b2c3",
    decrypted_size: int = DECRYPTED_SIZE,
) -> models.FileInternallyRegistered:
    """Generate a FileInternallyRegistered object for testing"""
    return models.FileInternallyRegistered(
        file_id=file_id or uuid4(),
        archive_date=now_utc_ms_prec(),
        storage_alias=storage_alias,
        bucket_id="permanent",
        secret_id="some-secret",
        decrypted_size=decrypted_size,
        encrypted_size=decrypted_size + 1000,
        decrypted_sha256=decrypted_sha256,
        encrypted_parts_md5=["a1b2c3", "d4e5f6"],
        encrypted_parts_sha256=["a1b2c3", "d4e5f6"],
        part_size=10000,
    )


def make_metadata_dataset_overview(
    accession: str = "DS001",
    files: list[event_schemas.MetadataDatasetFile] | None = None,
) -> event_schemas.MetadataDatasetOverview:
    """Generate a MetadataDatasetOverview object for testing"""
    if files is None:
        files = [
            event_schemas.MetadataDatasetFile(
                accession=ACCESSION1, description=None, file_extension=".bam"
            ),
            event_schemas.MetadataDatasetFile(
                accession=ACCESSION2, description=None, file_extension=".bam"
            ),
        ]
    return event_schemas.MetadataDatasetOverview(
        accession=accession,
        title="Test Dataset",
        stage=event_schemas.MetadataDatasetStage.DOWNLOAD,
        description=None,
        dac_alias="DAC001",
        dac_email="dac@example.com",
        files=files,
    )


def make_accession_map(
    accession: str = "GHGA001",
    file_id: UUID4 | None = None,
) -> models.FileAccessionMap:
    """Generate a FileAccessionMap object for testing"""
    return models.FileAccessionMap(accession=accession, file_id=file_id or uuid4())


def make_file_information(accession: str = "GHGA001") -> models.FileInformation:
    """Generate a FileInformation object for testing"""
    return models.FileInformation(
        accession=accession,
        size=12345678,
        storage_alias="HD01",
        sha256_hash="a1b2c3",
    )
