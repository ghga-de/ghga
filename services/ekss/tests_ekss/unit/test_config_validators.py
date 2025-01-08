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

"""Testing the basics of the service API"""

import pytest

from ekss.config import CONFIG, Config


def test_private_key():
    """Test server private key validator"""
    public_key = CONFIG.server_public_key
    private_key = CONFIG.server_private_key.get_secret_value()

    with pytest.raises(ValueError, match="Incorrect padding"):
        _ = Config(server_public_key=public_key, server_private_key="abc" + private_key)

    with pytest.raises(
        ValueError, match="Length of decoded private key did not match expectation"
    ):
        _ = Config(
            server_public_key=public_key, server_private_key="abcd" + private_key
        )


def test_public_key():
    """Test server public key validator"""
    public_key = CONFIG.server_public_key
    private_key = CONFIG.server_private_key.get_secret_value()

    with pytest.raises(ValueError, match="Incorrect padding"):
        _ = Config(server_public_key="abc" + public_key, server_private_key=private_key)
    with pytest.raises(
        ValueError, match="Length of decoded public key did not match expectation"
    ):
        _ = Config(
            server_public_key="abcd" + public_key, server_private_key=private_key
        )
