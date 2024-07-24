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
"""Config-related tests."""

import pytest
from pydantic import SecretStr

from sms.config import Config


def test_prefix_config():
    """Make sure you can't accidentally configure an empty prefix."""
    with pytest.raises(ValueError):
        Config(
            token_hashes=[],
            db_connection_str=SecretStr(""),
            db_prefix="",
            service_instance_id="1",
        )

    Config(
        token_hashes=[],
        db_connection_str=SecretStr(""),
        db_prefix="",
        allow_empty_prefix=True,
        service_instance_id="1",
    )

    Config(
        token_hashes=[],
        db_connection_str=SecretStr(""),
        db_prefix="test",
        allow_empty_prefix=True,
        service_instance_id="1",
    )

    Config(
        token_hashes=[],
        db_connection_str=SecretStr(""),
        db_prefix="test",
        allow_empty_prefix=False,
        service_instance_id="1",
    )
