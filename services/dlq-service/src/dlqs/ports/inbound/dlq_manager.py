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
"""DLQ Manager Port definition"""

from abc import ABC, abstractmethod
from uuid import UUID

from dlqs.models import EventCore, PublishableEventData, RawDLQEvent, StoredDLQEvent


class DLQManagerPort(ABC):
    """Manager for the Dead Letter Queue (DLQ) service"""

    class NotConfiguredError(RuntimeError):
        """Raised when the requested service & topic combination is not configured."""

        def __init__(self, *, service: str, topic: str):
            msg = (
                f"No matching configuration for service '{service}' and topic '{topic}'"
            )
            super().__init__(msg)

    class DLQValidationError(RuntimeError):
        """Raised when an event from the DLQ fails validation."""

        def __init__(self, *, dlq_id: UUID, reason: str):
            msg = f"Validation failed for DLQ Event '{dlq_id}': {reason}"
            super().__init__(msg)

    class DLQOperationError(RuntimeError):
        """Raised when an operation on the DLQ fails."""

    class DLQDeletionError(DLQOperationError):
        """Raised when an existing event could not be deleted from the DLQ."""

        def __init__(self, *, dlq_id: UUID):
            msg = (
                f"Could not delete DLQ event '{dlq_id}' from the database."
                + " Maybe the event was already deleted or the database is unreachable."
            )
            super().__init__(msg)

    class DLQInsertionError(DLQOperationError):
        """Raised when an event could not be inserted into the DLQ."""

        def __init__(self, *, dlq_id: UUID, already_exists: bool):
            msg = f"Could not insert DLQ event '{dlq_id}' into the database."
            if already_exists:
                msg += " Event with same ID already exists."
            super().__init__(msg)

    class DLQFetchNextError(DLQOperationError):
        """Raised when the next event from the DLQ could not be fetched."""

        def __init__(self, *, service: str, topic: str):
            msg = f"Failed to get next DLQ event for service '{service}' and topic '{topic}'"
            super().__init__(msg)

    class DLQPreviewError(DLQOperationError):
        """Raised when the next events from the DLQ could not be previewed."""

        def __init__(self, *, service: str, topic: str):
            msg = f"Failed to preview next DLQ events for service '{service}' and topic '{topic}'"
            super().__init__(msg)

    class DLQSequenceError(DLQOperationError):
        """Raised when the DLQ event ID is not next in the sequence"""

        def __init__(self, *, dlq_id: UUID, service: str, topic: str, next_id: UUID):
            msg = (
                f"The dlq_id of the next event for service '{service}' and topic"
                + f" '{topic}' is '{next_id}', but got '{dlq_id}'"
            )
            super().__init__(msg)

    class DLQEmptyError(DLQOperationError):
        """Raised when the user tries to process an empty DLQ"""

        def __init__(self, *, service: str, topic: str):
            msg = f"No DLQ events exist for service '{service}' and topic '{topic}'"
            super().__init__(msg)

    @abstractmethod
    async def store_event(self, *, event: RawDLQEvent) -> None:
        """Store an event in the database with its service name and event ID.

        Raises a `DLQInsertionError` if the insertion fails.
        """
        ...

    @abstractmethod
    async def preview_events(
        self,
        *,
        service: str,
        topic: str,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[StoredDLQEvent]:
        """Return a list of the next DLQ events for the given `service` and `topic`.

        Args:
        - `service`: The name of the service to preview events for.
        - `topic`: The name of the topic to preview.
        - `skip`: The number of events to skip for pagination. Default is 0.
        - `limit`: The maximum number of events to return. Default is None (no limit).

        Raises:
        - `ValueError` if there is a problem with the params supplied to the aggregator.
        - `DLQPreviewError` if the preview fails during the aggregation
        """
        ...

    @abstractmethod
    async def process_event(
        self,
        *,
        service: str,
        topic: str,
        dlq_id: UUID,
        override: EventCore | None,
        dry_run: bool,
    ) -> PublishableEventData:
        """Process the next event from the DLQ for the given `service` and `topic`.

        Args:
        - `service`: The service name for the DLQ to process.
        - `topic`: The topic name for the DLQ to process.
        - `dlq_id`: The ID of the DLQ event to process.
        - `override`: An optional event to publish instead of the next event.
        - `dry_run`: Whether to actually publish the event to the retry topic.

        Returns the event that was or would be published.

        Raises:
        - `DLQSequenceError`: if the dlq_id is not next in the event sequence.
        - `DLQEmptyError` if the DLQ for the service and topic is empty.
        - `DLQFetchNextError` if retrieval of the next event fails due to a DB error.
        - `DLQValidationError` if the event fails validation (e.g. invalid topic).
        - `DLQDeletionError` if the event could not be deleted from the DB after processing.
        """
        ...

    @abstractmethod
    async def discard_event(self, *, dlq_id: UUID) -> None:
        """Discard (delete) the next DLQ event for the given `service` and `topic`.

        This operation skips validation and auto-processing, simply deleting the event.
        If the event doesn't exist, nothing happens.

        Raises:
        - `DLQDeletionError` if the event exists, but could not be deleted.
        """
        ...
