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

"""Outbound DAO adapter — wires DTO models to MongoDB/Kafka via the outbox pattern."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from hexkit.custom_types import JsonObject
from hexkit.providers.mongokafka import MongoKafkaDaoPublisherFactory

from rs.config import Config
from rs.core.models import AltAccession
from rs.ports.outbound.dao import AltAccessionDao


def alt_accession_to_event(alt_accession: AltAccession) -> JsonObject:
    """Map an AltAccession DTO to its Kafka event payload."""
    return {"accession": alt_accession.pid, "file_id": alt_accession.id}


@asynccontextmanager
async def get_alt_accession_dao(
    *,
    config: Config,
    dao_publisher_factory: MongoKafkaDaoPublisherFactory,
) -> AsyncGenerator[AltAccessionDao]:
    """Construct an AltAccession DAO from the shared factory."""
    alt_accession_dao = await dao_publisher_factory.get_dao(
        name=config.alt_accessions_collection,
        dto_model=AltAccession,
        id_field="pid",
        dto_to_event=alt_accession_to_event,
        event_topic=config.alt_accessions_topic,
        autopublish=True,
    )
    yield alt_accession_dao
