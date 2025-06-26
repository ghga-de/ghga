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

"""DAO implementation"""

from hexkit.protocols.dao import DaoFactoryProtocol

from rts.models import Metadata
from rts.ports.outbound.dao import MetadataDao

METADATA_COLLECTION = "metadata"


async def get_metadata_dao(*, dao_factory: DaoFactoryProtocol) -> MetadataDao:
    """Construct a metadata DAO from the provided dao_factory"""
    return await dao_factory.get_dao(
        name=METADATA_COLLECTION,
        dto_model=Metadata,
        id_field="study_id",
    )
