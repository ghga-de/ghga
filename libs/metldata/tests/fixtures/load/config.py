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

from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from pydantic.env_settings import BaseSettings

from metldata.load.config import ArtifactLoaderAPIConfig
from tests.fixtures.load.utils import BASE_DIR

TEST_CONFIG_YAML = BASE_DIR / "test_config.yaml"


def get_config(
    sources: Optional[List[Union[BaseSettings, dict]]] = None,
    default_config_yaml: Path = TEST_CONFIG_YAML,
) -> ArtifactLoaderAPIConfig:
    """Merges parameters from the default TEST_CONFIG_YAML with params inferred
    from testcontainers."""
    sources_dict: Dict[str, object] = {}

    if sources is not None:
        for source in sources:
            if isinstance(source, BaseSettings):
                sources_dict.update(**source.dict())
            else:
                sources_dict.update(**source)

    with open(default_config_yaml, "r", encoding="UTF-8") as file:
        default_config = yaml.safe_load(file)

    return ArtifactLoaderAPIConfig(**default_config, **sources_dict)  # type: ignore
