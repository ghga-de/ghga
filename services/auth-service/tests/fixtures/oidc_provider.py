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

"""A mock of the OIDC provider that the auth adapter calls.

This lives apart from the other test utils because the root `conftest` imports it, and
at that point the signing keys that `utils` builds at import time do not exist yet.
"""

__all__ = ["USER_INFO", "OidcProviderMock", "mock_userinfo"]

from collections.abc import Mapping
from typing import Any

from ghga_service_commons.api.mock_api import ApiMock, endpoint, respond
from tests.fixtures.constants import EXT_ID_OF_JOHN

USER_INFO = {
    "name": "John Doe",
    "email": "john@home.org",
    "sub": EXT_ID_OF_JOHN,
}


class OidcProviderMock(ApiMock):
    """A mock of the OIDC provider endpoints that the auth adapter calls.

    The provider is mounted under a configurable URL, so the path below is matched
    against the end of the request URLs only. Every request that reaches the mock is
    recorded in `requests`.
    """

    on_userinfo = endpoint("GET", "/userinfo")


def mock_userinfo(
    oidc_provider: OidcProviderMock, user_info: Mapping[str, Any] = USER_INFO
) -> None:
    """Have the OIDC provider answer its userinfo endpoint with the given claims."""
    oidc_provider.on_userinfo = respond(200, json=dict(user_info))
