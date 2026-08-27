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
#

"""A mock of the access API, built on the service commons `ApiMock`."""

__all__ = ["AccessApiMock"]

from ghga_service_commons.api.mock_api import ApiMock, endpoint, respond
from wps.adapters.outbound.http import AccessCheckConfig

DOWNLOAD_PATH = "/download-access/users/{user_id}"
UPLOAD_PATH = "/upload-access/users/{user_id}"


class AccessApiMock(ApiMock):
    """A mock of the access API endpoints that the work package service talks to.

    Each endpoint answers with the handler currently assigned to the matching `on_...`
    attribute. Tests can swap those out with `respond(...)` or any other callable
    taking the request. Every request that reaches the mock is recorded in `requests`,
    so tests can assert which URL was actually requested.
    """

    on_check_download_access = endpoint(
        "GET", f"{DOWNLOAD_PATH}/datasets/{{dataset_id}}", respond(json=None)
    )
    on_get_accessible_datasets = endpoint(
        "GET", f"{DOWNLOAD_PATH}/datasets", respond(json={})
    )
    on_check_upload_access = endpoint(
        "GET", f"{UPLOAD_PATH}/boxes/{{box_id}}", respond(json=None)
    )
    on_get_accessible_boxes = endpoint("GET", f"{UPLOAD_PATH}/boxes", respond(json={}))

    def __init__(self, *, config: AccessCheckConfig) -> None:
        """Serve the access API where the given config expects it."""
        super().__init__(base_url=str(config.access_url))

    @property
    def last_url(self) -> str:
        """The URL of the most recent request that reached the mock."""
        return str(self.last_request.url)
