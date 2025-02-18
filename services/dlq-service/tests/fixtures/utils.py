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

"""Contains functions to generate DLQ events for different topics, as well as
helper functions and constants for testing purposes.
"""

from typing import Literal
from uuid import uuid4

from hexkit.providers.akafka.provider.eventsub import HeaderNames

from dlqs.models import DLQInfo, RawDLQEvent, StoredDLQEvent
from tests.fixtures.config import DEFAULT_CONFIG

# Service names
UFS = "ufs"
FSS = "fss"

# Topic names
NOTIFICATIONS = "notifications"
USER_EVENTS = "user-events"
GRAPH_UPDATES = "graph-updates"
EventLocation = Literal["dlq", "retry"]
TEST_CID = "387a028c-a272-4086-b930-6d3e3c389d51"
VALID_AUTH_HEADER = {"Authorization": "Bearer 43fadc91-b98f-4925-bd31-1b054b13dc55"}
INVALID_AUTH_HEADER = {"Authorization": "Bearer 63fadc92-b98f-4926-bd30-1b054b13dc56"}


def dlq_to_db(event: RawDLQEvent) -> StoredDLQEvent:
    """Convert an EventInfo instance to a StoredDLQEvent instance.

    This performs the transformation that occurs when storing a DLQ event in the DB.
    """
    event_id = event.headers.pop(HeaderNames.EVENT_ID)
    service, _, partition, offset = event_id.split(",")
    dlq_info = DLQInfo(
        service=service,
        partition=int(partition),
        offset=int(offset),
        exc_class=event.headers.pop(HeaderNames.EXC_CLASS, ""),
        exc_msg=event.headers.pop(HeaderNames.EXC_MSG, ""),
    )

    db_event = StoredDLQEvent(
        dlq_id=uuid4(),
        topic=event.headers.pop(HeaderNames.ORIGINAL_TOPIC),
        type_=event.type_,
        payload=event.payload,
        key=event.key,
        timestamp=event.timestamp,
        headers=event.headers,
        dlq_info=dlq_info,
    )
    return db_event


def user_event(*, service: Literal["ufs", "fss"], offset: int = 0) -> RawDLQEvent:
    """Generate a DLQ event for the user-events topic.

    Works with either the UFS (user feed service) or the FSS (friend suggestion service)
    """
    user_id = f"user_id{offset}"
    headers = {
        HeaderNames.ORIGINAL_TOPIC: USER_EVENTS,
        HeaderNames.EVENT_ID: f"{service},{USER_EVENTS},0,{offset}",
        HeaderNames.EXC_CLASS: "ResourceAlreadyExistsError",
        HeaderNames.EXC_MSG: f'The resource with the id "{user_id}" already exists.',
        HeaderNames.CORRELATION_ID: TEST_CID,
    }

    dlq_user_event = RawDLQEvent(
        topic=DEFAULT_CONFIG.kafka_dlq_topic,
        type_="registration",
        payload={"user_id": user_id, "name": "John Doe"},
        key=user_id,
        headers=headers,
    )
    return dlq_user_event


def notifications_event(*, offset: int = 0) -> RawDLQEvent:
    """Generate a DLQ event for the notifications topic.

    Only for the UFS (user feed service).
    """
    user_id1 = f"user_id{offset}"
    user_id2 = f"user_id{offset + 1}"
    headers = {
        HeaderNames.ORIGINAL_TOPIC: NOTIFICATIONS,
        HeaderNames.EVENT_ID: f"{UFS},{NOTIFICATIONS},0,{offset}",
        HeaderNames.EXC_CLASS: "ResourceNotFoundError",
        HeaderNames.EXC_MSG: f'The resource with the id "{user_id2}" does not exist.',
        HeaderNames.CORRELATION_ID: TEST_CID,
    }

    notifications_event = RawDLQEvent(
        topic=DEFAULT_CONFIG.kafka_dlq_topic,
        type_="tagged_in_photo",
        payload={
            "photo_id": "76dc2b15-38e5-4e67-9ee9-7da031d7fc45",
            "tagger_id": user_id1,
            "tagged_id": user_id2,
            "msg": "You were tagged in a photo",
        },
        key=user_id2,
        headers=headers,
    )
    return notifications_event


def graph_event(*, offset: int = 0) -> RawDLQEvent:
    """Generate a DLQ event for the graph-updates topic.

    Only for the FSS (friend suggestion service).
    """
    user_id1 = f"user_id{offset}"
    user_id2 = f"user_id{offset + 1}"
    headers = {
        HeaderNames.ORIGINAL_TOPIC: GRAPH_UPDATES,
        HeaderNames.EVENT_ID: f"{FSS},{GRAPH_UPDATES},0,{offset}",
        HeaderNames.EXC_CLASS: "ResourceNotFoundError",
        HeaderNames.EXC_MSG: f'The resource with the id "{user_id2}" does not exist.',
        HeaderNames.CORRELATION_ID: TEST_CID,
    }

    graph_event = RawDLQEvent(
        topic=DEFAULT_CONFIG.kafka_dlq_topic,
        type_="connection_added",
        payload={"source_id": user_id1, "dest_id": user_id2},
        key=user_id1,
        headers=headers,
    )
    return graph_event
