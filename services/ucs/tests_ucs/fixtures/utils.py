# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from ghga_event_schemas.pydantic_ import FileUploadReceived
from ghga_service_commons.utils.utc_dates import now_as_utc

BASE_DIR = Path(__file__).parent.resolve()


def null_func(*args, **kwargs):
    """I am accepting any args and kwargs but I am doing nothing."""
    pass


def is_success_http_code(http_code: int) -> bool:
    """Checks if a http response code indicates success (a 2xx code)."""
    return http_code >= 200 and http_code < 300


def make_test_event(file_id: str) -> FileUploadReceived:
    """Return a FileUploadReceived event with the given file ID."""
    event = FileUploadReceived(
        upload_date=now_as_utc().isoformat(),
        file_id=file_id,
        object_id="",
        bucket_id="",
        s3_endpoint_alias="",
        decrypted_size=0,
        submitter_public_key="",
        expected_decrypted_sha256="",
    )
    return event
