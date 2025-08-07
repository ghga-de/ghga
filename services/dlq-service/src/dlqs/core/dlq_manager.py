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

"""Domain logic for the DLQ Service"""

import logging
from contextlib import suppress
from uuid import UUID

from hexkit.correlation import set_correlation_id
from hexkit.protocols.dao import ResourceAlreadyExistsError
from hexkit.protocols.eventpub import EventPublisherProtocol
from hexkit.providers.akafka.provider.eventsub import HeaderNames

from dlqs.config import Config
from dlqs.models import (
    DLQInfo,
    EventCore,
    PublishableEventData,
    RawDLQEvent,
    StoredDLQEvent,
)
from dlqs.ports.inbound.dlq_manager import DLQManagerPort
from dlqs.ports.outbound.dao import AggregatorPort, EventDaoPort, ResourceNotFoundError

log = logging.getLogger(__name__)


def stored_event_from_raw_event(event: RawDLQEvent) -> StoredDLQEvent:
    """Convert a RawDLQEvent object to a StoredDLQEvent object

    When events are published to the DLQ from the consuming service, they are given
    a new event ID, and the old one goes into the headers as original_event_id.
    The new event ID is used as the DLQ ID, and the old event ID is stored in DLQInfo.
    """
    # Extract the DLQ info from the headers
    og_topic = event.headers[HeaderNames.ORIGINAL_TOPIC]
    service = event.headers.get(HeaderNames.SERVICE_NAME, "")

    og_event_id = (
        UUID(event.headers.get(HeaderNames.ORIGINAL_EVENT_ID))
        if HeaderNames.ORIGINAL_EVENT_ID in event.headers
        else None
    )
    if not og_event_id:
        log.info(
            "DLQ Event %s did not arrive with an existing 'original_event_id'",
            event.dlq_id,
        )
    exc_class = event.headers.get(HeaderNames.EXC_CLASS, "")
    exc_msg = event.headers.get(HeaderNames.EXC_MSG, "")
    dlq_info = DLQInfo(
        service=service,
        original_event_id=og_event_id,
        exc_class=exc_class,
        exc_msg=exc_msg,
    )

    # Create the final object to be stored in the database
    stored_event = StoredDLQEvent(
        dlq_id=event.dlq_id,
        topic=og_topic,
        type_=event.type_,
        payload=event.payload,
        key=event.key,
        timestamp=event.timestamp,
        headers={HeaderNames.CORRELATION_ID: event.headers[HeaderNames.CORRELATION_ID]},
        dlq_info=dlq_info,
    )
    return stored_event


class DLQManager(DLQManagerPort):
    """Manager for the Dead Letter Queue (DLQ) service"""

    def __init__(
        self,
        config: Config,
        publisher: EventPublisherProtocol,
        dao: EventDaoPort,
        aggregator: AggregatorPort,
    ):
        self._config = config
        self._publisher = publisher
        self._dao = dao
        self._aggregator = aggregator

    async def _get_next_event(
        self, *, service: str, topic: str
    ) -> StoredDLQEvent | None:
        """Get the next event from the DLQ for the given `service` and `topic`.

        Returns the next event or `None` if no events are found.

        Raises a `DLQFetchNextError` if the operation fails.
        """
        try:
            events = await self._aggregator.aggregate(
                service=service, topic=topic, limit=1
            )
            if events:
                return events[0]
        except Exception as err:
            error = self.DLQFetchNextError(service=service, topic=topic)
            log.error(error)
            raise error from err

        log.debug("No DLQ events found for service %s and topic %s", service, topic)
        return None

    def _validate_event(self, *, event: EventCore) -> None:
        """Validate the event before processing it.

        Ensures that:
        - The topic field is not set to a retry topic.

        Raises a `ValueError` if any of the above conditions are not met.
        """
        # Original topic for inbound event shouldn't be DLQ topic or a retry topic
        if (
            event.topic.startswith("retry-")
            or event.topic == self._config.kafka_dlq_topic
        ):
            raise ValueError(f"Resolved event topic can't be set to '{event.topic}'")

    async def store_event(self, *, event: RawDLQEvent) -> None:
        """Store an event in the database with its service name and event ID.

        Raises a `DLQInsertionError` if the insertion fails.
        """
        stored_event = stored_event_from_raw_event(event)
        try:
            await self._dao.insert(stored_event)
        except Exception as err:
            already_exists = isinstance(err, ResourceAlreadyExistsError)
            error = self.DLQInsertionError(
                dlq_id=stored_event.dlq_id,
                already_exists=already_exists,
            )
            log.error(error, exc_info=not already_exists)  # log TB if misc
            raise error from err

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
        try:
            events = await self._aggregator.aggregate(
                service=service, topic=topic, skip=skip, limit=limit
            )
        except AggregatorPort.AggregationError as err:
            error = self.DLQPreviewError(service=service, topic=topic)
            log.error(error)
            raise error from err

        return [StoredDLQEvent(**event.model_dump()) for event in events]

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
        next_event = await self._get_next_event(service=service, topic=topic)
        if not next_event:
            empty_dlq_error = self.DLQEmptyError(service=service, topic=topic)
            log.error(empty_dlq_error)
            raise empty_dlq_error
        elif next_event.dlq_id != dlq_id:
            # If the supplied dlq ID doesn't match that of the next event, raise an error
            sequence_error = self.DLQSequenceError(
                dlq_id=dlq_id, service=service, topic=topic, next_id=next_event.dlq_id
            )
            log.error(sequence_error)
            raise sequence_error

        # Get the correlation ID from the stored event
        correlation_id = UUID(next_event.headers.pop(HeaderNames.CORRELATION_ID))

        # Distill the main publishable event data (we don't care about the rest)
        core_publish_data = override or EventCore(**next_event.model_dump())

        # Perform event validation
        try:
            self._validate_event(event=core_publish_data)
        except ValueError as err:
            dlq_error = self.DLQValidationError(dlq_id=dlq_id, reason=str(err))
            log.error(dlq_error)
            raise dlq_error from err

        # The only header required now is the original topic header
        publish_data = PublishableEventData(
            **core_publish_data.model_dump(),
            headers={HeaderNames.ORIGINAL_TOPIC: core_publish_data.topic},
        )
        publish_data.topic = f"retry-{service}"

        # If this isn't a dry-run, actually publish the event to the retry topic
        if not dry_run:
            async with set_correlation_id(correlation_id):
                await self._publisher.publish(**publish_data.model_dump())

            # Remove the resolved event from the database
            await self.discard_event(dlq_id=dlq_id)
        return publish_data

    async def discard_event(self, *, dlq_id: UUID) -> None:
        """Discard (delete) the next DLQ event for the given `service` and `topic`.

        This operation skips validation and auto-processing, simply deleting the event.
        If the event doesn't exist, nothing happens.

        Raises:
        - `DLQDeletionError` if the event exists, but could not be deleted.
        """
        try:
            with suppress(ResourceNotFoundError):
                await self._dao.delete(dlq_id)
                log.debug("Deleted DLQ event with ID '%s'", dlq_id)
        except Exception as err:
            error = self.DLQDeletionError(dlq_id=dlq_id)
            log.error(error)
            raise error from err
