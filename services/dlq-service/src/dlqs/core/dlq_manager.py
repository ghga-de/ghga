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

"""Domain logic for the DLQ Service"""

import base64
import json
import logging
import re
from collections import Counter, defaultdict
from contextlib import suppress
from typing import Any, NoReturn
from uuid import UUID

from dlqs.config import Config
from dlqs.models import (
    DLQInfo,
    EventCore,
    PublishableEventData,
    RawDLQEvent,
    StoredDLQEvent,
)
from dlqs.ports.inbound.dlq_manager import DLQManagerPort
from dlqs.ports.outbound.dao import EventDaoPort, ResourceNotFoundError
from hexkit.correlation import set_correlation_id
from hexkit.protocols.dao import DbTimeoutError, ResourceAlreadyExistsError
from hexkit.protocols.eventpub import EventPublisherProtocol
from hexkit.providers.akafka import KafkaEventSubscriber
from hexkit.providers.akafka.provider.eventsub import HeaderNames

log = logging.getLogger(__name__)

# Stored for a missing or unusable service or topic, since the API addresses events
# by both; such events can only be discarded
UNKNOWN = "unknown"
# What a Kafka topic name may hold; a service name is held to the same, so that
# both fit into a URL path segment
_VALID_NAME = re.compile(r"[A-Za-z0-9._-]{1,249}")

# The exception a subscriber reports for a record it could not decode
MALFORMED_RECORD_EXC_CLASS = KafkaEventSubscriber.MalformedRecordError.__name__

# A subscriber wraps a payload in these fields when it cannot publish the original
# to the DLQ, for an undecodable record or one that is too large once re-encoded
_RAW_VALUE_WRAPPER_FIELDS = {"raw_value_b64", "decode_error"}

# The payload fields of a degraded copy, by which it is recognized
_DEGRADED_COPY_FIELDS = {"payload_json_b64", "payload_truncated", "store_error"}

# Limits for a degraded copy, which must fit into a 16 MiB MongoDB document: the
# payload's JSON bytes, before the base64 encoding adds a third, and other strings
_DEGRADED_PAYLOAD_MAX_BYTES = 11 * 1024 * 1024
_DEGRADED_TEXT_MAX_CHARS = 4000


def _valid_name_or_unknown(name: str | None, *, what: str, dlq_id: UUID) -> str:
    """Return the name if the API can address it, otherwise `UNKNOWN`."""
    # Kafka forbids "." and "..", and a URL path cannot carry them as a segment
    if name and _VALID_NAME.fullmatch(name) and name not in (".", ".."):
        return name
    log.warning(
        "DLQ event %s arrived with %s %s, storing it as '%s'",
        dlq_id,
        f"an unusable {what}" if name else f"no {what}",
        ascii(name[:100]) if name else "",
        UNKNOWN,
    )
    return UNKNOWN


def is_degraded_copy(event: StoredDLQEvent) -> bool:
    """Whether the event is a degraded copy, recognized by its payload fields."""
    return event.payload.keys() >= _DEGRADED_COPY_FIELDS


def original_payload(event: StoredDLQEvent) -> dict[str, Any] | None:
    """Return the payload a degraded copy holds, or None if it was cut or lost."""
    payload = event.payload
    if payload.get("payload_truncated") or not payload.get("payload_json_b64"):
        return None
    try:
        original = json.loads(base64.b64decode(payload["payload_json_b64"]))
    except Exception:
        return None
    return original if isinstance(original, dict) else None


def degraded_copy(event: StoredDLQEvent, *, error: Exception) -> StoredDLQEvent:
    """Return a copy of the event that MongoDB can store.

    Some valid JSON cannot be stored: a NUL byte or a lone surrogate in a string,
    an integer beyond 64 bits, or deep nesting. The copy keeps the payload as
    base64-encoded JSON, cut if needed, and every other string within limits.
    """
    try:
        raw: bytes | None = json.dumps(event.payload).encode("ascii")
    except Exception:  # also RecursionError for deeply nested payloads
        raw = None
    truncated = raw is not None and len(raw) > _DEGRADED_PAYLOAD_MAX_BYTES
    store_error = f"{type(error).__name__}: {error}"
    payload: dict[str, Any] = {
        "payload_json_b64": (
            None
            if raw is None
            else base64.b64encode(raw[:_DEGRADED_PAYLOAD_MAX_BYTES]).decode("ascii")
        ),
        "payload_truncated": truncated,
        "store_error": store_error.encode("ascii", errors="backslashreplace").decode(
            "ascii"
        )[:_DEGRADED_TEXT_MAX_CHARS],
    }
    max_chars = _DEGRADED_TEXT_MAX_CHARS
    dlq_info = event.dlq_info.model_copy(
        update={
            "exc_class": event.dlq_info.exc_class[:max_chars],
            "exc_msg": event.dlq_info.exc_msg[:max_chars],
        }
    )
    return event.model_copy(
        update={
            "payload": payload,
            "key": event.key[:max_chars],
            "type_": event.type_[:max_chars],
            "dlq_info": dlq_info,
        }
    )


def stored_event_from_raw_event(event: RawDLQEvent) -> StoredDLQEvent:
    """Convert a RawDLQEvent object to a StoredDLQEvent object

    When events are published to the DLQ from the consuming service, they are given
    a new event ID, and the old one goes into the headers as original_event_id.
    The new event ID is used as the DLQ ID, and the old event ID is stored in DLQInfo.
    """
    # Extract the DLQ info from the headers
    og_topic = _valid_name_or_unknown(
        event.headers.get(HeaderNames.ORIGINAL_TOPIC),
        what="original topic",
        dlq_id=event.dlq_id,
    )
    service = _valid_name_or_unknown(
        event.headers.get(HeaderNames.SERVICE_NAME),
        what="service name",
        dlq_id=event.dlq_id,
    )

    og_event_id: UUID | None = None
    found_event_id = event.headers.get(HeaderNames.ORIGINAL_EVENT_ID)
    if found_event_id is None:
        log.info(
            "DLQ Event %s did not arrive with an existing 'original_event_id'",
            event.dlq_id,
        )
    else:
        with suppress(ValueError):
            og_event_id = UUID(found_event_id)
        if og_event_id is None or og_event_id.version != 4:
            log.warning(
                "DLQ Event %s arrived with an invalid 'original_event_id': %r",
                event.dlq_id,
                found_event_id[:100],
            )
            og_event_id = None
    exc_class = event.headers.get(HeaderNames.EXC_CLASS, "")
    exc_msg = event.headers.get(HeaderNames.EXC_MSG, "")
    dlq_info = DLQInfo(
        service=service,
        original_event_id=og_event_id,
        exc_class=exc_class,
        exc_msg=exc_msg,
    )

    # Create the final object to be stored in the database
    return StoredDLQEvent(
        dlq_id=event.dlq_id,
        topic=og_topic,
        type_=event.type_,
        payload=event.payload,
        key=event.key,
        timestamp=event.timestamp,
        headers={HeaderNames.CORRELATION_ID: event.headers[HeaderNames.CORRELATION_ID]},
        dlq_info=dlq_info,
    )


class DLQManager(DLQManagerPort):
    """Manager for the Dead Letter Queue (DLQ) service"""

    def __init__(
        self,
        config: Config,
        publisher: EventPublisherProtocol,
        dao: EventDaoPort,
    ):
        self._config = config
        self._publisher = publisher
        self._dao = dao

    async def _get_next_event(
        self, *, service: str, topic: str
    ) -> StoredDLQEvent | None:
        """Get the next event from the DLQ for the given `service` and `topic`.

        Returns the next event or `None` if no events are found.

        Raises a `DLQFetchNextError` if the operation fails.
        """
        try:
            events = [
                x
                async for x in self._dao.find_all(
                    filter_={"dlq_info.service": service, "topic": topic},
                    sort=["timestamp"],
                    limit=1,
                )
            ]
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
        - The topic field is not set to a retry topic, the DLQ topic or `unknown`.

        Raises a `ValueError` if any of the above conditions are not met.
        """
        # Original topic for inbound event shouldn't be DLQ topic or a retry topic,
        # and an unknown one would send the event nowhere
        if event.topic.startswith("retry-") or event.topic in (
            self._config.kafka_dlq_topic,
            UNKNOWN,
        ):
            raise ValueError(f"Resolved event topic can't be set to '{event.topic}'")

    @staticmethod
    def _reason_not_to_publish(
        *, event: StoredDLQEvent, override: EventCore | None
    ) -> str | None:
        """Return why the event cannot be requeued, or None if it can.

        An event of an unknown service has no retry topic to go to. The payload of a
        malformed record is a wrapper, not the original payload, and so is that of a
        degraded copy whose payload was cut, so such an event can only be requeued
        with an override. A degraded copy that holds its whole payload is requeued
        with that payload.
        """
        if event.dlq_info.service == UNKNOWN:
            return "the event's service is unknown, so it can only be discarded"
        if override is None:
            if event.dlq_info.exc_class == MALFORMED_RECORD_EXC_CLASS:
                return "the event is a malformed record, so it needs an override"
            if is_degraded_copy(event):
                if original_payload(event) is None:
                    return "the event's payload was cut when stored, so it needs an override"
                return None
            if event.payload.keys() >= _RAW_VALUE_WRAPPER_FIELDS:
                return "the event's payload is a wrapper, so it needs an override"
        return None

    async def store_event(self, *, event: RawDLQEvent) -> None:
        """Store an event in the database with its service name and event ID.

        An event that cannot be stored as it is gets stored as a degraded copy,
        since the DLQ service has no DLQ of its own and would otherwise stop on it.

        Raises a `DLQInsertionError` if the insertion fails, and on a timeout.
        """
        stored_event = stored_event_from_raw_event(event)
        try:
            await self._dao.insert(stored_event)
        except ResourceAlreadyExistsError:
            # Each DLQ publish gets a new event ID, so this is a redelivery
            log.info("DLQ event %s is already stored", stored_event.dlq_id)
        except DbTimeoutError as err:
            self._raise_insertion_error(dlq_id=stored_event.dlq_id, err=err)
        except Exception as err:
            # Encoding errors fail the same way on every attempt; other database
            # errors may be either kind. If the database is down, the degraded
            # copy fails as well and the error is raised.
            log.error(
                "Could not store DLQ event %s as it is, storing a degraded copy",
                stored_event.dlq_id,
                exc_info=True,
            )
            await self._store_degraded_copy(stored_event, error=err)

    async def _store_degraded_copy(
        self, stored_event: StoredDLQEvent, *, error: Exception
    ) -> None:
        """Store a degraded copy of an event that could not be stored as it is."""
        try:
            await self._dao.insert(degraded_copy(stored_event, error=error))
        except ResourceAlreadyExistsError:
            log.info("DLQ event %s is already stored", stored_event.dlq_id)
        except Exception as err:
            self._raise_insertion_error(dlq_id=stored_event.dlq_id, err=err)

    def _raise_insertion_error(self, *, dlq_id: UUID, err: Exception) -> NoReturn:
        """Log and raise a `DLQInsertionError` caused by the given error."""
        error = self.DLQInsertionError(dlq_id=dlq_id, already_exists=False)
        log.error(error, exc_info=True)
        raise error from err

    async def get_service_topic_summary(self) -> dict[str, Counter[str]]:
        """Returns a dictionary containing an overview of the contents of the DLQS
        for operational convenience. The dict's keys are the available services, and the
        values are another dict containing the number of DLQ events for each topic.

        Example:
        ```python
        {
            "service-A": {"topic-A": 5, "topic-B": 1},
            "service-B": {"topic-B": 4}
        }
        ```
        """
        service_topics: dict[str, Counter[str]] = defaultdict(Counter)

        # TODO: Here we pull back everything just to get a couple fields - this is a
        # limitation of hexkit and is costly/inefficient. Should optimize in the future.
        results_iter = self._dao.find_all(filter_={})
        async for event in results_iter:
            service_topics[event.dlq_info.service][event.topic] += 1
        return service_topics

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
        - `DLQPaginationError` if there is a problem with the skip or limit parameters.
        - `DLQPreviewError` if the preview fails for any other reason.
        """
        try:
            return [
                x
                async for x in self._dao.find_all(
                    filter_={"dlq_info.service": service, "topic": topic},
                    sort=["timestamp"],
                    skip=skip,
                    limit=limit,
                )
            ]
        except ValueError as err:
            raise self.DLQPaginationError() from err
        except Exception as err:
            error = self.DLQPreviewError(service=service, topic=topic)
            log.error(error)
            raise error from err

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
        - `DLQValidationError` if the event fails validation (e.g. invalid topic),
          if its service is unknown, or if its payload is a wrapper or was cut when
          stored and no override is given.
        - `DLQDeletionError` if the event could not be deleted from the DB after processing.
        """
        next_event = await self._get_next_event(service=service, topic=topic)
        if not next_event:
            empty_dlq_error = self.DLQEmptyError(service=service, topic=topic)
            log.error(empty_dlq_error)
            raise empty_dlq_error
        if next_event.dlq_id != dlq_id:
            # If the supplied dlq ID doesn't match that of the next event, raise an error
            sequence_error = self.DLQSequenceError(
                dlq_id=dlq_id, service=service, topic=topic, next_id=next_event.dlq_id
            )
            log.error(sequence_error)
            raise sequence_error

        # Checked before anything is published, in a dry run as well
        reason = self._reason_not_to_publish(event=next_event, override=override)
        if reason:
            dlq_error = self.DLQValidationError(dlq_id=dlq_id, reason=reason)
            log.error(dlq_error)
            raise dlq_error

        # Get the correlation ID from the stored event
        correlation_id = UUID(next_event.headers.pop(HeaderNames.CORRELATION_ID))

        # Distill the main publishable event data (we don't care about the rest)
        core_publish_data = override or EventCore(**next_event.model_dump())
        if override is None and is_degraded_copy(next_event):
            # Checked above: a degraded copy without an override holds its payload
            core_publish_data.payload = original_payload(next_event) or {}

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
