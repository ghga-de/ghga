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
"""Config Parameter Modeling and Parsing"""

from ghga_service_commons.api import ApiConfigBase
from hexkit.config import config_from_yaml
from hexkit.log import LoggingConfig
from hexkit.providers.akafka import KafkaConfig

from fis.adapters.outbound.event_pub import EventPubTranslatorConfig
from fis.adapters.outbound.vault import VaultConfig
from fis.core.ingest import ServiceConfig


@config_from_yaml(prefix="fis")
class Config(
    ApiConfigBase,
    EventPubTranslatorConfig,
    KafkaConfig,
    ServiceConfig,
    VaultConfig,
    LoggingConfig,
):
    """Config parameters and their defaults."""

    service_name: str = "fis"


CONFIG = Config()  # type: ignore [call-arg]
