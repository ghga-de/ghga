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

"""Test the tokens module."""

from ghga_service_commons.utils.jwt_helpers import (
    decode_and_validate_token,
    generate_jwk,
)

from wps.core.models import WorkOrderToken, WorkType
from wps.core.tokens import (
    generate_work_package_access_token,
    hash_token,
    sign_work_order_token,
)


def test_generate_work_package_access_token():
    """Test the generation of a work package access token."""
    token = generate_work_package_access_token()
    assert len(token) == 24
    assert token.isascii()
    assert token.isalnum()
    another_token = generate_work_package_access_token()
    assert len(another_token) == len(token)
    assert another_token.isascii()
    assert another_token.isalnum()
    assert another_token != token


def test_hash_token():
    """Test hashing of tokens."""
    token = "abc123" * 4
    hashed_token = hash_token(token)
    assert 16 <= len(hashed_token) <= 64
    assert hashed_token.isascii()
    hashed_again_token = hash_token(token)
    assert hashed_again_token == hashed_token
    another_token = "123abc" * 4
    hashed_another_token = hash_token(another_token)
    assert hashed_another_token != hashed_token


def test_sign_work_order_token():
    """Test signing of work order tokens."""
    key = generate_jwk()
    work_order_token = WorkOrderToken(
        type=WorkType.DOWNLOAD,
        file_id="some-file-id",
        file_ext=".some-ext",
        user_id="some-user-id",
        public_key="some-public-key",
        full_user_name="Dr. John Doe",
        email="john@home.org",
    )
    token_str = sign_work_order_token(work_order_token=work_order_token, key=key)
    assert isinstance(token_str, str)
    assert len(token_str) > 80
    assert token_str.count(".") == 2
    token_chars = token_str.replace(".", "").replace("-", "").replace("_", "")
    assert token_chars.isalnum()
    assert token_chars.isascii()
    token_dict = decode_and_validate_token(token_str, key)
    assert isinstance(token_dict, dict)
    assert token_dict.pop("exp") - token_dict.pop("iat") == 30
    expected_token_dict = work_order_token.dict()
    assert token_dict == expected_token_dict
