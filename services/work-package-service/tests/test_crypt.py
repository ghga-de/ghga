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

"""Test the helper functions for encryption."""

import base64

import pytest

from wps.core.crypt import validate_public_key


def encode(key: bytes) -> str:
    """Get base64 encoded key."""
    return base64.b64encode(key).decode("ascii")


def test_valid_public_key():
    """Test that a valid public key passes."""
    key = encode(b"foo-bar." * 4)  # 32 bytes
    assert validate_public_key(key) == key


def test_empty_public_key():
    """Test that an empty public key does not pass."""
    with pytest.raises(ValueError, match="empty"):
        assert validate_public_key(None)  # type: ignore
    with pytest.raises(ValueError, match="empty"):
        assert validate_public_key("")
    with pytest.raises(ValueError, match="Invalid"):
        assert validate_public_key("null")


def test_invalid_public_key():
    """Test that an invalid public key does not pass."""
    key = encode(b"foo-bar." * 2)  # 16 bytes
    with pytest.raises(ValueError, match="Invalid"):
        assert validate_public_key(key)
    key = encode(b"foo-bar." * 5)  # 50 bytes
    with pytest.raises(ValueError, match="Invalid"):
        assert validate_public_key(key)


def test_private_key_instead_of_public_key():
    """Test that passing a private key throws."""
    key = encode(b"c4gh-v1" + 46 * b"x")
    with pytest.raises(ValueError, match="Invalid"):
        validate_public_key(key)


def test_valid_public_key_wrapped_as_crypt4gh_public_key():
    """Test that a properly wrapped valid public key passes.

    Also test that only the key itself is returned.
    """
    key = encode(b"bar-baz." * 4)
    wrapped_key = (
        "-----BEGIN CRYPT4GH PUBLIC KEY-----\n"
        + key
        + "\n-----END CRYPT4GH PUBLIC KEY-----\n"
    )
    assert validate_public_key(wrapped_key) == key


def test_private_key_wrapped_as_crypt4gh_public_key():
    """Test that a private key wrapped as public throws."""
    key = encode(b"c4gh-v1" + 46 * b"x")
    wrapped_key = (
        "-----BEGIN CRYPT4GH PUBLIC KEY-----\n"
        + key
        + "\n-----END CRYPT4GH PUBLIC KEY-----\n"
    )
    with pytest.raises(ValueError, match="Invalid"):
        validate_public_key(wrapped_key)


def test_valid_public_key_wrapped_as_non_crypt4gh_public_key():
    """Test that wrapping as a non Crypt4GH public key throws."""
    key = encode(b"bar-baz." * 4)
    wrapped_key = (
        "-----BEGIN CRYPT9GH PUBLIC KEY-----\n"
        + key
        + "\n-----END CRYPT9GH PUBLIC KEY-----\n"
    )
    with pytest.raises(ValueError, match="Invalid"):
        validate_public_key(wrapped_key)


def test_valid_public_key_wrapped_as_crypt4gh_private_key():
    """Test that wrapping as a Crypt4GH private key throws."""
    key = encode(b"bar-baz." * 4)
    wrapped_key = (
        "-----BEGIN CRYPT4GH PRIVATE KEY-----\n"
        + key
        + "\n-----END CRYPT4GH PRIVATE KEY-----\n"
    )
    with pytest.raises(ValueError, match="Do not pass a private key"):
        validate_public_key(wrapped_key)
