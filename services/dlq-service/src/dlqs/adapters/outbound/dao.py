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
"""DAO and Aggregator implementation"""

import logging
from typing import Any

from hexkit.protocols.dao import DaoFactoryProtocol
from hexkit.providers.mongodb.provider import document_to_dto
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo.errors import OperationFailure

from dlqs.config import Config
from dlqs.models import StoredDLQEvent
from dlqs.ports.outbound.dao import AggregatorPort, EventDaoPort

log = logging.getLogger(__name__)

DLQ_EVENTS_COLLECTION = "dlqEvents"


async def get_event_dao(*, dao_factory: DaoFactoryProtocol) -> EventDaoPort:
    """Construct a DLQ Event DAO  from the provided dao_factory"""
    return await dao_factory.get_dao(
        name=DLQ_EVENTS_COLLECTION,
        dto_model=StoredDLQEvent,
        id_field="dlq_id",
        # fields_to_index=["dlq_info.service", "topic"],  # Add in the future
    )


class Aggregator(AggregatorPort):
    """Aggregator for DLQ events"""

    def __init__(self, *, collection: AsyncIOMotorCollection) -> None:
        """Initialize with a MongoDB collection"""
        self._collection = collection

    async def aggregate(
        self, *, service: str, topic: str, skip: int = 0, limit: int | None = None
    ) -> list[StoredDLQEvent]:
        """Aggregate events from the DLQ by service and topic.

        Args:
        - `service`: The service name to match against.
        - `topic`: The topic name to match against.
        - `skip`: The number of events to skip for pagination.
        - `limit`: The maximum number of events to return for pagination.

        Raises:
        - `ValueError` if `skip` or `limit` is invalid.
        - `AggregationError` if the aggregation fails.
        """
        if skip < 0:
            raise ValueError(f"Skip must be 0 or greater, got {skip}")

        if limit is not None and limit < 1:
            raise ValueError(f"Limit must be greater than 0 if supplied, got {limit}")

        pipeline: list[dict[str, Any]] = [
            {"$match": {"dlq_info.service": service, "topic": topic}},
            {"$sort": {"timestamp": 1}},
        ]

        if skip:
            pipeline.append({"$skip": skip})

        if limit:
            pipeline.append({"$limit": limit})

        try:
            results = self._collection.aggregate(pipeline=pipeline)
            return [
                document_to_dto(item, id_field="dlq_id", dto_model=StoredDLQEvent)
                async for item in results
            ]
        except OperationFailure as err:
            params_as_string = f"{{{service=}, {topic=}, {skip=}, {limit=}}}"
            agg_error = self.AggregationError(parameters=params_as_string)
            log.error(agg_error)
            raise agg_error from err


def get_aggregator(*, config: Config) -> Aggregator:
    """Return an Aggregator with a collection set up"""
    timeout_ms = (
        int(config.mongo_timeout * 1000) if config.mongo_timeout is not None else None
    )
    client: AsyncIOMotorClient = AsyncIOMotorClient(
        str(config.mongo_dsn.get_secret_value()),
        timeoutMS=timeout_ms,
    )
    db = client[config.db_name]
    collection = db[DLQ_EVENTS_COLLECTION]
    return Aggregator(collection=collection)
