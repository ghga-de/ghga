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
"""A mock of the external OIDC provider the auth adapter calls.

Kept apart from `utils`, which pulls in the service configuration - `conftest` needs
this before that configuration is in place.
"""

from ghga_service_commons.api.mock_api import MockedApi, endpoint

__all__ = ["MockedOidcApi"]


class MockedOidcApi(MockedApi):
    """A mock of the external OIDC provider the auth adapter calls."""

    base_url = "https://login.aai.lifescience-ri.eu/oidc"

    on_userinfo = endpoint("GET", "/userinfo")
