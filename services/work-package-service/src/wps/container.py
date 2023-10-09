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
from hexkit.providers.akafka import KafkaEventSubscriber
from hexkit.providers.mongodb import MongoDbDaoFactory

from wps.adapters.inbound.event_sub import EventSubTranslator
from wps.adapters.outbound.dao import DatasetDaoConstructor, WorkPackageDaoConstructor
from wps.adapters.outbound.http import AccessCheckAdapter
from wps.config import Config
from wps.core.repository import WorkPackageRepository


class Container(ContainerBase):
    """DI Container"""

    config = get_configurator(Config)

    # outbound providers:
    dao_factory = get_constructor(MongoDbDaoFactory, config=config)

    # outbound translators:
    work_package_dao = get_constructor(
        WorkPackageDaoConstructor,
        config=config,
        dao_factory=dao_factory,
    )
    dataset_dao = get_constructor(
        DatasetDaoConstructor,
        config=config,
        dao_factory=dao_factory,
    )

    # auth provider:
    auth_provider = get_constructor(
        GHGAAuthContextProvider,
        config=config,
        context_class=AuthContext,
    )

    # download access adapter:
    download_access_checks = get_constructor(AccessCheckAdapter, config=config)

    # core components:
    work_package_repository = get_constructor(
        WorkPackageRepository,
        config=config,
        access_check=download_access_checks,
        dataset_dao=dataset_dao,
        work_package_dao=work_package_dao,
    )

    # inbound translators:
    event_sub_translator = get_constructor(
        EventSubTranslator,
        work_package_repository=work_package_repository,
        config=config,
    )

    # inbound providers:
    event_subscriber = get_constructor(
        KafkaEventSubscriber, config=config, translator=event_sub_translator
    )
