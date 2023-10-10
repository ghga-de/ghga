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
"""Test config"""

from pathlib import Path

from tests.fixtures.utils import BASE_DIR
from wkvs.config import Config

TEST_CONFIG_YAML = BASE_DIR / "test_config.yaml"


def get_config(
    default_config_yaml: Path = TEST_CONFIG_YAML,
) -> Config:
    """Load test config"""
    return Config(config_yaml=default_config_yaml)  # type: ignore[call-arg]
