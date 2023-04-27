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

"""Test the cryptographic utilities."""


import base64

from nacl.public import PrivateKey, PublicKey
from pytest import raises

from ghga_service_commons.utils.crypt import (
    KeyPair,
    decode_key,
    decrypt,
    encode_key,
    encrypt,
    generate_key_pair,
)


def test_generate_key_pair():
    """Test that random key pairs can be generated."""
    key_pair = generate_key_pair()
    assert isinstance(key_pair, KeyPair)
    assert key_pair.private != key_pair.public
    assert len(key_pair.private) == len(key_pair.public)
    another_key_pair = generate_key_pair()
    assert another_key_pair.private != another_key_pair.public
    assert len(another_key_pair.private) == len(another_key_pair.public)
    assert another_key_pair != key_pair
    assert key_pair.private != another_key_pair.private
    assert key_pair.public != another_key_pair.public


def test_decode_valid_key():
    """Test that valid base64 encoded keys can be decoded."""
    assert decode_key(base64.b64encode(b"foo4" * 8).decode("ascii")) == b"foo4" * 8


def test_decode_invalid_key():
    """Test that invalid base64 encoded can be detected."""
    with raises(ValueError, match="Incorrect padding"):
        decode_key("foo")
    with raises(ValueError, match="Invalid key"):
        decode_key(base64.b64encode(b"foo").decode("ascii"))


def test_encode_valid_key():
    """Test that valid raw keys can be encoded."""
    assert encode_key(b"foo4" * 8) == base64.b64encode(b"foo4" * 8).decode("ascii")


def test_encode_invalid_key():
    """Test that invalid raw keys can be detected."""
    with raises(ValueError, match="Invalid key"):
        encode_key(b"foo")


def test_encode_and_decode_key_pair():
    """Test that keys from key pairs can be base64 encoded and decoded."""
    key_pair = generate_key_pair()
    for raw in key_pair:
        encoded = encode_key(raw)
        assert isinstance(encoded, str)
        assert encoded.isascii()
        assert len(encoded) > len(raw)
        assert decode_key(encoded) == raw


def test_encryption_and_decryption_with_raw_keys():
    """Test encrypting and decrypting a message with raw keys."""
    key_pair = generate_key_pair()

    message = "Foo bar baz!"

    encrypted = encrypt(message, key_pair.public)
    assert isinstance(encrypted, str)
    assert encrypted != message

    decrypted = decrypt(encrypted, key_pair.private)
    assert isinstance(decrypted, str)
    assert decrypted == message


def test_encryption_and_decryption_with_encoded_keys():
    """Test encrypting and decrypting a message with base64 encoded keys."""
    key_pair = generate_key_pair()

    message = "Foo bar baz!"

    encrypted = encrypt(message, encode_key(key_pair.public))
    assert isinstance(encrypted, str)
    assert encrypted != message

    decrypted = decrypt(encrypted, encode_key(key_pair.private))
    assert isinstance(decrypted, str)
    assert decrypted == message


def test_encryption_and_decryption_with_key_objects():
    """Test encrypting and decrypting a message with key objects."""
    key_pair = generate_key_pair()

    message = "Foo bar baz!"

    encrypted = encrypt(message, PublicKey(key_pair.public))
    assert isinstance(encrypted, str)
    assert encrypted != message

    decrypted = decrypt(encrypted, PrivateKey(key_pair.private))
    assert isinstance(decrypted, str)
    assert decrypted == message


def test_encryption_and_decryption_with_private_key_only():
    """Test encrypting and decrypting with private key and derived public key."""
    key_pair = generate_key_pair()
    private_key = PrivateKey(key_pair.private)

    message = "Foo bar baz!"

    encrypted = encrypt(message, private_key)
    assert isinstance(encrypted, str)
    assert encrypted != message

    decrypted = decrypt(encrypted, private_key)
    assert isinstance(decrypted, str)
    assert decrypted == message


def test_encryption_with_encoded_and_decryption_with_raw_key():
    """Test encrypting with base64 encoded key and decrypting with raw key."""
    key_pair = generate_key_pair()

    message = "Foo bar baz!"

    encrypted = encrypt(message, encode_key(key_pair.public))
    assert isinstance(encrypted, str)
    assert encrypted != message

    decrypted = decrypt(encrypted, key_pair.private)
    assert isinstance(decrypted, str)
    assert decrypted == message


def test_encrypt_same_message_twice():
    """Test encrypting the same message message twice.

    Note that the results should be different because ephemeral keys are used
    to actually encrypt the messages.
    """
    key_pair = generate_key_pair()

    message = "Foo bar baz!"

    encrypted = encrypt(message, key_pair.public)
    assert encrypted != message
    encrypted_again = encrypt(message, key_pair.public)
    assert encrypted_again != message

    assert encrypted != encrypted_again
    assert decrypt(encrypted, key_pair.private) == message
    assert decrypt(encrypted_again, key_pair.private) == message


def test_encrypted_is_encoded_and_raw_data_can_be_decrypted():
    """Test that encrypted data is base64 encoded and that raw data can be decrypted."""
    key_pair = generate_key_pair()

    message = "Foo bar baz!"

    encrypted = encrypt(message, key_pair.public)
    assert isinstance(encrypted, str)
    encrypted_raw = base64.b64decode(encrypted)

    decrypted = decrypt(encrypted_raw, key_pair.private)
    assert isinstance(decrypted, str)
    assert decrypted == message


def test_encryption_and_decryption_with_non_ascii_data():
    """Test encrypting and decrypting a non ASCII message with raw keys."""
    key_pair = generate_key_pair()

    message = "Ƒø båřȑ bāç‼"
    assert not message.isascii()

    encrypted = encrypt(message, key_pair.public)
    assert isinstance(encrypted, str)
    assert encrypted.isascii()

    decrypted = decrypt(encrypted, key_pair.private)
    assert isinstance(decrypted, str)
    assert decrypted == message
