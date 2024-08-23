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

from sms.config import Config
from tests.fixtures.config import DEFAULT_TEST_CONFIG


def adapt_default_config(config: dict) -> dict:
    """Adapt the default config to the test's needs."""
    test_config = DEFAULT_TEST_CONFIG.model_dump()
    test_config.update(config)
    return test_config


def test_prefix_config():
    """Make sure you can't accidentally configure an empty prefix."""
    with pytest.raises(ValueError):
        vals = adapt_default_config({"db_prefix": ""})
        Config(**vals)

    Config(**adapt_default_config({"db_prefix": "", "allow_empty_prefix": True}))

    Config(**adapt_default_config({"db_prefix": "test", "allow_empty_prefix": True}))

    Config(**adapt_default_config({"db_prefix": "test", "allow_empty_prefix": False}))
