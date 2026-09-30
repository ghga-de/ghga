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

"""A mock of the OIDC provider the auth adapter asks for user info."""

import httpx2

from ghga_service_commons.http.mock_api import MockApi, NotMockedError, ResponseHandler

__all__ = ["OidcProviderMock"]


def _userinfo_not_set(request: httpx2.Request) -> httpx2.Response:
    """Refuse to make up user info the test did not ask for."""
    raise NotMockedError(f"Call mock_userinfo() before requesting {request.url}")


class OidcProviderMock(MockApi):
    """A mock of the OIDC userinfo endpoint, answering only after `mock_userinfo`."""

    def __init__(self, userinfo_endpoint: str) -> None:
        super().__init__(userinfo_endpoint)
        self.on_get_userinfo: ResponseHandler = _userinfo_not_set
        self.route("GET", "", "on_get_userinfo")  # the endpoint is the whole API
