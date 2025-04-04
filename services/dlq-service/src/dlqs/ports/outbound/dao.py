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
"""Dao and Aggregator port definitions"""

from abc import ABC, abstractmethod

from hexkit.protocols.dao import Dao, ResourceNotFoundError  # noqa: F401

from dlqs.models import StoredDLQEvent

EventDaoPort = Dao[StoredDLQEvent]


class AggregatorPort(ABC):
    """Definition of a class that aggregates events from the DLQ by service and topic"""

    class AggregationError(RuntimeError):
        """Raised when something goes wrong with the aggregation operation"""

        def __init__(self, *, parameters: str):
            msg = f"Failed to aggregate events using the parameters {parameters}."
            super().__init__(msg)

    @abstractmethod
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
        - `AggregationError` if the event retrieval fails.
        """
        ...
