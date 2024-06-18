# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Example data used for testing."""

from dataclasses import dataclass

from ghga_event_schemas.pydantic_ import MetadataSubmissionFiles
from ghga_service_commons.utils.utc_dates import now_as_utc

from ucs.core import models


@dataclass
class UploadDetails:
    """Compact container for necessary test data"""

    storage_alias: str
    file_metadata: models.FileMetadata
    upload_attempt: models.UploadAttempt
    submission_metadata: MetadataSubmissionFiles


STORAGE_ALIASES = ("test", "test2")

# Example metadata for a single file:
EXAMPLE_FILE_1 = models.FileMetadata(
    file_id="testFile001",
    file_name="Test File 001",
    decrypted_sha256="fake-checksum",
    decrypted_size=12345678,
    latest_upload_id="testUpload001",
)
EXAMPLE_FILE_2 = EXAMPLE_FILE_1.model_copy(
    update={
        "file_id": "testFile002",
        "file_name": "Test File 002",
        "latest_upload_id": "testUpload002",
    }
)

# Details on an example upload corresponding to the respective EXAMPLE_FILE:
EXAMPLE_UPLOAD_1 = models.UploadAttempt(
    upload_id="testUpload001",
    file_id=EXAMPLE_FILE_1.file_id,
    object_id="object001",
    status=models.UploadStatus.PENDING,
    part_size=1234,
    creation_date=now_as_utc(),
    submitter_public_key="test-key",
    completion_date=None,
    storage_alias=STORAGE_ALIASES[0],
)
EXAMPLE_UPLOAD_2 = EXAMPLE_UPLOAD_1.model_copy(
    update={
        "upload_id": "testUpload002",
        "object_id": "object002",
        "file_id": EXAMPLE_FILE_2.file_id,
        "storage_alias": STORAGE_ALIASES[1],
    }
)

# Metadata for file submission
FILE_TO_REGISTER_1 = MetadataSubmissionFiles(
    file_id=EXAMPLE_FILE_1.file_id,
    file_name=EXAMPLE_FILE_1.file_name,
    decrypted_size=EXAMPLE_FILE_1.decrypted_size,
    decrypted_sha256=EXAMPLE_FILE_1.decrypted_sha256,
)
FILE_TO_REGISTER_2 = MetadataSubmissionFiles(
    file_id=EXAMPLE_FILE_2.file_id,
    file_name=EXAMPLE_FILE_2.file_name,
    decrypted_size=EXAMPLE_FILE_2.decrypted_size,
    decrypted_sha256=EXAMPLE_FILE_2.decrypted_sha256,
)


UPLOAD_DETAILS_1 = UploadDetails(
    storage_alias=STORAGE_ALIASES[0],
    file_metadata=EXAMPLE_FILE_1,
    upload_attempt=EXAMPLE_UPLOAD_1,
    submission_metadata=FILE_TO_REGISTER_1,
)
UPLOAD_DETAILS_2 = UploadDetails(
    storage_alias=STORAGE_ALIASES[0],
    file_metadata=EXAMPLE_FILE_2,
    upload_attempt=EXAMPLE_UPLOAD_2,
    submission_metadata=FILE_TO_REGISTER_2,
)
