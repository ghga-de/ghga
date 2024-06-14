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

"""Logic that isn't directly owned by the file registry but is used by it."""

import logging
from contextlib import suppress
from typing import TypeVar

from hexkit.correlation import get_correlation_id
from hexkit.protocols.dao import DaoNaturalId, NoHitsFoundError
from pydantic import BaseModel

from ifrs.adapters.inbound import models

log = logging.getLogger(__name__)

RecordType = TypeVar("RecordType", bound=models.IdempotenceRecord)


def make_record_from_update(
    record_type: type[RecordType], update: BaseModel
) -> RecordType:
    """Get an IdempotenceRecord containing the update payload and correlation ID."""
    correlation_id = get_correlation_id()
    return record_type(correlation_id=correlation_id, **update.model_dump())


async def check_record_is_new(
    dao: DaoNaturalId,
    resource_id: str,
    update: BaseModel,
    record: models.IdempotenceRecord,
):
    """Returns whether or not the record is new and emits a debug log if it is not."""
    with suppress(NoHitsFoundError):
        matching_record = await dao.find_one(mapping=record.model_dump())

        if matching_record:
            log.debug(
                (
                    "Event with '%s' schema for resource ID '%s' has"
                    + " already been processed under current correlation_id. Skipping."
                ),
                type(update).__name__,
                resource_id,
            )
            return False
    return True
