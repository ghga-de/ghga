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

import base64

from pytest import raises

from wps.core.crypt import decode_public_key, encrypt

from .fixtures.crypt import decrypt, user_public_crypt4gh_key


def test_decode_public_key():
    """Test that invalid public keys can be detected."""
    with raises(ValueError, match="Incorrect padding"):
        decode_public_key("foo")
    with raises(ValueError, match="The public key must be exactly 32 bytes long"):
        decode_public_key(base64.b64encode(b"foo").decode("ascii"))
    decode_public_key(base64.b64encode(b"foo4" * 8).decode("ascii"))
    decode_public_key(user_public_crypt4gh_key)


def test_encrypt():
    """Test that ASCII strings can be properly encrypted."""
    data = "Hello, World!"
    encrypted_data = encrypt(data, user_public_crypt4gh_key)
    decrypted_data = decrypt(encrypted_data)
    assert decrypted_data == data
