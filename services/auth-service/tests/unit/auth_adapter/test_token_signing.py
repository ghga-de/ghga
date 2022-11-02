# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

"""Unit tests for the core token signing feature"""

from pytest import raises

from auth_service.auth_adapter.core.auth import (
    TokenSigningError,
    jwt_config,
    sign_and_encode_token,
)

from ...fixtures.utils import get_claims_from_token


def test_signs_and_encodes_an_internal_token():
    """Test that internal tokens can be signed and encoded."""
    claims = {"foo": "bar"}
    internal_token = sign_and_encode_token(claims)
    assert internal_token is not None
    assert get_claims_from_token(internal_token) == claims


def test_does_not_sign_an_empty_payload():
    """Test that an empty payload is rejected."""
    with raises(TokenSigningError, match="No payload"):
        sign_and_encode_token(None)  # type: ignore
    with raises(TokenSigningError, match="No payload"):
        sign_and_encode_token({})


def test_does_not_sign_internal_token_when_internal_key_is_missing():
    """Test that internal tokens cannot be signed without an internal key."""
    claims = {"foo": "bar"}
    internal_jwk, jwt_config.internal_jwk = jwt_config.internal_jwk, None
    try:
        with raises(TokenSigningError) as exc_info:
            sign_and_encode_token(claims)
    finally:
        jwt_config.internal_jwk = internal_jwk
    assert str(exc_info.value) == "No internal signing key, cannot sign token."
