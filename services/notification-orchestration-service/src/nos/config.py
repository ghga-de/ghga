# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Config Parameter Modeling and Parsing."""

from hexkit.config import config_from_yaml
from hexkit.log import LoggingConfig
from hexkit.providers.akafka import KafkaConfig
from hexkit.providers.mongodb.migrations import MigrationConfig
from pydantic import Field

from nos.adapters.inbound.event_sub import (
    EventSubTranslatorConfig,
    OutboxSubTranslatorConfig,
)
from nos.adapters.outbound.event_pub import NotificationEmitterConfig

SERVICE_NAME: str = "nos"


@config_from_yaml(prefix=SERVICE_NAME)
class Config(
    LoggingConfig,
    KafkaConfig,
    EventSubTranslatorConfig,
    OutboxSubTranslatorConfig,
    NotificationEmitterConfig,
    MigrationConfig,
):
    """Config parameters and their defaults."""

    service_name: str = Field(
        default=SERVICE_NAME,
        description=(
            "The Notification Orchestration Service controls the creation of"
            + " notification events."
        ),
    )

    central_data_stewardship_email: str = Field(
        default=...,
        description="The email address of the central data steward.",
    )

    helpdesk_email: str = Field(
        default=..., description="The email address of the GHGA Helpdesk."
    )
