# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""DAO implementation"""

import logging

from hexkit.protocols.dao import DaoFactoryProtocol
from hexkit.providers.mongodb.provider import MongoDbIndex

from dlqs.models import StoredDLQEvent
from dlqs.ports.outbound.dao import EventDaoPort

log = logging.getLogger(__name__)

DLQ_EVENTS_COLLECTION = "dlqEvents"


async def get_event_dao(*, dao_factory: DaoFactoryProtocol) -> EventDaoPort:
    """Construct a DLQ Event DAO  from the provided dao_factory"""
    return await dao_factory.get_dao(
        name=DLQ_EVENTS_COLLECTION,
        dto_model=StoredDLQEvent,
        id_field="dlq_id",
        indexes=[MongoDbIndex(fields={"dlq_info.service": 1, "topic": 1})],
    )
