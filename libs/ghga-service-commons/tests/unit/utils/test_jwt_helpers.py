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

"""Test the utils.jwt_helpers module."""

import pytest
from jwcrypto.common import JWException

from ghga_service_commons.utils.jwt_helpers import (
    decode_and_validate_token,
    generate_jwk,
    sign_and_serialize_token,
)


def test_sign_and_validate():
    """Test that JSON Web Tokens can be signed and validated."""
    key = generate_jwk()
    key_dict = key.export(as_dict=True)
    assert isinstance(key_dict, dict)
    assert key_dict["kty"] == "EC" and key_dict["crv"] == "P-256"
    assert key_dict["d"] and key_dict["x"] and key_dict["y"]
    claims = {"name": "John Doe", "status": "VIP"}
    token = sign_and_serialize_token(claims, key, valid_seconds=300)
    assert isinstance(token, str)
    assert len(token) > 80
    assert token.count(".") == 2
    chars = token.replace(".", "").replace("-", "").replace("_", "")
    assert chars.isalnum()
    assert chars.isascii()
    token_dict = decode_and_validate_token(token, key)
    assert isinstance(token_dict, dict)
    assert token_dict.pop("exp") - token_dict.pop("iat") == 300
    assert token_dict == claims
    # Change the first character of the signature: changing the last one can
    # leave non-canonical base64, which jwcrypto rejects before verifying.
    head, signature = token.rsplit(".", 1)
    signature = ("B" if signature[0] == "A" else "A") + signature[1:]
    token = f"{head}.{signature}"
    with pytest.raises(JWException, match="Verification failed"):
        decode_and_validate_token(token, key)


def test_sign_leaves_out_none_claims():
    """Test that claims with the value None are not put into the token."""
    key = generate_jwk()
    token = sign_and_serialize_token({"name": "John Doe", "title": None}, key)
    token_dict = decode_and_validate_token(token, key)
    assert "title" not in token_dict
    assert token_dict["name"] == "John Doe"
