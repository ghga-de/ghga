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

"""Test config"""

from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, YamlConfigSettingsSource

from sms.config import Config
from tests.fixtures.utils import BASE_DIR

TEST_CONFIG_YAML = BASE_DIR / "test_config.yaml"


def get_config(
    sources: list[BaseSettings] | None = None,
    default_config_yaml: Path = TEST_CONFIG_YAML,
) -> Config:
    """Merges parameters from the default TEST_CONFIG_YAML with params inferred
    from testcontainers.
    """
    test_config = YamlConfigSettingsSource(BaseSettings, default_config_yaml, "utf-8")
    sources_dict: dict[str, Any] = test_config.yaml_data

    if sources is not None:
        for source in sources:
            # Only update with keys that are already in the test config yaml
            source_dump = source.model_dump()
            config_to_add = {k: v for k, v in source_dump.items() if k in sources_dict}
            sources_dict.update(**config_to_add)

    return Config(**sources_dict)


DEFAULT_TEST_CONFIG = get_config()
