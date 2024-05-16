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
#

"""Test the OIDC Discovery helper class."""

import json

import pytest

from auth_service.auth_adapter.core.auth import OIDCDiscovery

LS_AAI = "https://login.aai.lifescience-ri.eu/oidc/"


@pytest.fixture(name="discovery")
def discovery_fixture() -> OIDCDiscovery:
    """Create an OIDCDiscovery instance for the LS AAI OIDC authority."""
    return OIDCDiscovery(LS_AAI)


def test_ls_aai_issuer(discovery: OIDCDiscovery):
    """Test the issuer discovery."""
    assert discovery.issuer == LS_AAI


def test_ls_aai_jwks_str(discovery: OIDCDiscovery):
    """Test the JWKS discovery."""
    jwks_str = discovery.jwks_str
    assert jwks_str
    assert jwks_str.startswith("{")
    assert jwks_str.endswith("}")
    jwks = json.loads(jwks_str)
    assert "keys" in jwks
    assert isinstance(jwks["keys"], list)


def test_ls_aai_token_endpoint(discovery: OIDCDiscovery):
    """Test the userinfo endpoint discovery."""
    assert discovery.token_endpoint == LS_AAI + "token"


def test_ls_aai_userinfo_endpoint(discovery: OIDCDiscovery):
    """Test the userinfo endpoint discovery."""
    assert discovery.userinfo_endpoint == LS_AAI + "userinfo"
