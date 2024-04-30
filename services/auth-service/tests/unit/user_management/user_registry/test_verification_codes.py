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

"""Unit tests for verification code generation."""

from pytest import mark

from auth_service.user_management.user_registry.core.verification_codes import (
    generate_code,
    hash_code,
    validate_code,
)

DEFAULT_CODE_SIZE = 6  # the code size that we expect is used as the default
DEFAULT_SALT_SIZE = 16  # the size of the salt that we expect to be used by default
DEFAULT_HASH_SIZE = 64  # the size of the code hash that we expect to be used


@mark.parametrize("size", [DEFAULT_CODE_SIZE, 4, 8, 10, 12])
def test_generate_verification_code_with_various_size(size: int):
    """Test the generation of verification codes with alternative sizes."""
    codes = set()
    for _ in range(10 * size):
        # also test that 6 is the default size
        code = generate_code() if size == DEFAULT_CODE_SIZE else generate_code(size)
        codes.add(code)
        assert len(code) == size
        assert code.isascii()
        assert code.isalnum()
        assert code.isupper()
        assert sum(c.isalpha() for c in code) >= size // 3
        assert sum(c.isdigit() for c in code) >= size // 3
    assert len(codes) > 7.5 * size


TEST_CODES = [
    "ABC123",
    "P3Q4R5",
    "7C8D9E",
    "CODE",
    "1234",
    "123456",
    "ABCD1234",
    "ADMIN123",
    "TOPSECRET",
]


@mark.parametrize("code", TEST_CODES)
def test_hash_and_validate_code(code: str):
    """Test the hashing and validation of a selection of possible verification codes."""
    hash_with_salt = hash_code(code)
    assert len(hash_with_salt) == DEFAULT_SALT_SIZE + DEFAULT_HASH_SIZE
    assert hash_with_salt.isascii()
    assert set(hash_with_salt).issubset(set("0123456789abcdef"))
    assert validate_code(code, hash_with_salt)
    assert validate_code(code.lower(), hash_with_salt)
    assert not validate_code("RANDOM", hash_with_salt)
    assert not validate_code("654321", hash_with_salt)


def test_hash_and_validate_generated_codes():
    """Test the hashing and validation of randomly generated verification codes."""
    last_code = None
    for _ in range(100):
        code = generate_code()
        hash_with_salt = hash_code(code)
        assert len(hash_with_salt) == DEFAULT_SALT_SIZE + DEFAULT_HASH_SIZE
        assert hash_with_salt.isascii()
        assert set(hash_with_salt).issubset(set("0123456789abcdef"))
        assert validate_code(code, hash_with_salt)
        assert validate_code(code.lower(), hash_with_salt)
        if last_code:
            assert not validate_code(last_code, hash_with_salt)
        else:
            last_code = code
