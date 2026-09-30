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

"""A mock of the access API, built on the service commons `MockApi`."""

from ghga_service_commons.http.mock_api import MockApi, ResponseHandler, respond
from wps.adapters.outbound.http import AccessCheckConfig

__all__ = ["AccessApiMock"]


class AccessApiMock(MockApi):
    """A mock of the access API endpoints the WPS calls, granting no access by default.

    A JSON `null` answer is `respond(content=b"null")`, as `json=None` sends no body.
    """

    def __init__(self, *, config: AccessCheckConfig) -> None:
        super().__init__(str(config.access_url))
        self.on_check_download_access: ResponseHandler = respond(content=b"null")
        self.on_get_accessible_datasets: ResponseHandler = respond(json={})
        self.on_check_upload_access: ResponseHandler = respond(content=b"null")
        self.on_get_accessible_boxes: ResponseHandler = respond(json={})
        self.route(
            "GET",
            "/download-access/users/{user_id}/datasets/{dataset_id}",
            "on_check_download_access",
        )
        self.route(
            "GET",
            "/download-access/users/{user_id}/datasets",
            "on_get_accessible_datasets",
        )
        self.route(
            "GET",
            "/upload-access/users/{user_id}/boxes/{box_id}",
            "on_check_upload_access",
        )
        self.route(
            "GET", "/upload-access/users/{user_id}/boxes", "on_get_accessible_boxes"
        )

    @property
    def last_url(self) -> str:
        """The URL of the most recent request the mock served."""
        assert self.last_request is not None
        return str(self.last_request.url)
