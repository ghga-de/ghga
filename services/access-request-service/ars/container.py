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

"""Module hosting the dependency injection container."""

from ghga_service_commons.auth.ghga import AuthContext, GHGAAuthContextProvider
from hexkit.inject import ContainerBase, get_configurator, get_constructor
from hexkit.providers.akafka import KafkaEventPublisher
from hexkit.providers.mongodb import MongoDbDaoFactory

from ars.adapters.outbound.dao import AccessRequestDaoConstructor
from ars.adapters.outbound.event_pub import NotificationEmitter
from ars.config import Config
from ars.core.repository import AccessRequestRepository


class Container(ContainerBase):
    """DI Container"""

    config = get_configurator(Config)

    # outbound providers:
    dao_factory = get_constructor(MongoDbDaoFactory, config=config)

    event_publisher = get_constructor(KafkaEventPublisher, config=config)

    # outbound translators:
    access_request_dao = get_constructor(
        AccessRequestDaoConstructor,
        dao_factory=dao_factory,
    )

    notification_emitter = get_constructor(
        NotificationEmitter, config=config, event_publisher=event_publisher
    )

    # auth provider:
    auth_provider = get_constructor(
        GHGAAuthContextProvider,
        config=config,
        context_class=AuthContext,
    )

    access_request_repository = get_constructor(
        AccessRequestRepository,
        access_request_dao=access_request_dao,
        notification_emitter=notification_emitter,
        config=config,
    )
