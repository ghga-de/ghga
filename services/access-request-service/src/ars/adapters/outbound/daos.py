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
#

"""DAO translators for accessing the database."""

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.configs.stateful import AccessRequestEventsConfig
from hexkit.custom_types import JsonObject
from hexkit.protocols.dao import DaoFactoryProtocol
from hexkit.protocols.daopub import DaoPublisherFactoryProtocol

from ars.core import models
from ars.ports.outbound.daos import AccessRequestDaoPort, DatasetDaoPort

__all__ = ["AccessRequestDaoConfig", "get_access_request_dao", "get_dataset_dao"]


class AccessRequestDaoConfig(AccessRequestEventsConfig):
    """Config containing the event topic used to send Access Request events"""


def _access_request_to_event(access_request: models.AccessRequest) -> JsonObject:
    """Convert an access request object to a dumped AccessRequestDetails object."""
    event = event_schemas.AccessRequestDetails(
        id=access_request.id,
        user_id=access_request.user_id,
        dataset_id=access_request.dataset_id,
        dataset_title=access_request.dataset_title,
        dataset_description=access_request.dataset_description,
        status=access_request.status,
        request_text=access_request.request_text,
        dac_alias=access_request.dac_alias,
        access_starts=access_request.access_starts,
        access_ends=access_request.access_ends,
    )
    return event.model_dump()


async def get_access_request_dao(
    *,
    config: AccessRequestDaoConfig,
    dao_publisher_factory: DaoPublisherFactoryProtocol,
) -> AccessRequestDaoPort:
    """Get an Access Request DAO.

    This DAO automatically publishes changes as events.
    """
    return await dao_publisher_factory.get_dao(
        name="accessRequests",
        dto_model=models.AccessRequest,
        dto_to_event=_access_request_to_event,
        event_topic=config.access_request_topic,
        id_field="id",
    )


async def get_dataset_dao(*, dao_factory: DaoFactoryProtocol) -> DatasetDaoPort:
    """Get a Dataset DAO."""
    return await dao_factory.get_dao(
        name="datasets",
        dto_model=models.Dataset,
        id_field="id",
    )
