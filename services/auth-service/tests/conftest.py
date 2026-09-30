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

"""Fixtures that are shared between all unit and integration tests"""

import httpx2
import pytest

from auth_service.config import CONFIG
from tests.fixtures.oidc_provider import OidcProviderMock


@pytest.fixture
def oidc_provider(monkeypatch: pytest.MonkeyPatch) -> OidcProviderMock:
    """Provide a mock of the OIDC provider that answers the `httpx2.get` calls."""
    provider = OidcProviderMock(str(CONFIG.oidc_userinfo_endpoint))
    client = httpx2.Client(transport=provider.as_transport())
    monkeypatch.setattr(httpx2, "get", client.get)
    return provider
