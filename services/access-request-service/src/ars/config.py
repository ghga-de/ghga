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

"""Config Parameter Modeling and Parsing"""

from ghga_service_commons.api import ApiConfigBase
from ghga_service_commons.auth.ghga import AuthConfig
from hexkit.config import config_from_yaml
from hexkit.providers.akafka import KafkaConfig
from hexkit.providers.mongodb import MongoDbConfig

from ars.adapters.outbound.event_pub import NotificationEmitterConfig
from ars.adapters.outbound.http import AccessGrantsConfig
from ars.core.repository import AccessRequestConfig


@config_from_yaml(prefix="ars")
class Config(
    ApiConfigBase,
    AuthConfig,
    MongoDbConfig,
    KafkaConfig,
    NotificationEmitterConfig,
    AccessGrantsConfig,
    AccessRequestConfig,
):
    """Config parameters and their defaults."""

    service_name: str = "ars"
    db_name: str = "access-requests"

    notification_event_topic: str = "notifications"
    notification_event_type: str = "notification"

    access_upfront_max_days: int = 6 * 30
    access_grant_min_days: int = 7
    access_grant_max_days: int = 2 * 365
