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
#

"""Produce a DAO using a DAO factory"""

from hexkit.protocols.dao import DaoFactoryProtocol

from ns.models import EventId
from ns.ports.outbound.dao import EventIdDaoPort


async def get_event_id_dao(*, dao_factory: DaoFactoryProtocol) -> EventIdDaoPort:
    """Construct a EventIdDaoPort from the provided dao_factory"""
    return await dao_factory.get_dao(
        name="events",
        dto_model=EventId,
        id_field="event_id",
    )
