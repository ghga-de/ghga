# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from auth_service.auth_adapter.core.auth import OIDCDiscovery

LS_AAI = "https://proxy.aai.lifescience-ri.eu"


def test_ls_aai_issuer():
    """Test the issuer discovery."""
    discovery = OIDCDiscovery(LS_AAI)
    assert discovery.issuer == LS_AAI


def test_ls_aai_jwks_str():
    """Test the JWKS discovery."""
    discovery = OIDCDiscovery(LS_AAI)
    assert discovery.jwks_str.startswith('{"keys": [{')


def test_ls_aai_token_endpoint():
    """Test the userinfo endpoint discovery."""
    discovery = OIDCDiscovery(LS_AAI)
    assert discovery.token_endpoint == LS_AAI + "/OIDC/token"


def test_ls_aai_userinfo_endpoint():
    """Test the userinfo endpoint discovery."""
    discovery = OIDCDiscovery(LS_AAI)
    assert discovery.userinfo_endpoint == LS_AAI + "/OIDC/userinfo"
