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

"""FastAPI routes for Kafka state management."""

import re
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from sms.adapters.inbound.fastapi_ import dummies
from sms.adapters.inbound.fastapi_.http_authorization import (
    TokenAuthContext,
    require_token,
)
from sms.models import EventDetails

KAFKA_TOPIC_PATTERN = r"^[a-zA-Z0-9._-]+$"

kafka_router = APIRouter()


def is_topic_valid(topic: str) -> bool:
    """Validate a Kafka topic name. Return True if valid, False otherwise."""
    return re.match(KAFKA_TOPIC_PATTERN, topic) is not None


@kafka_router.delete(
    "/",
    operation_id="clear_topics",
    summary="Clear events from the given topic(s).",
    description=(
        "If no topics are specified, all topics will be cleared, except internal"
        + " topics unless otherwise specified."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_topics(
    events_handler: dummies.EventsHandlerPortDummy,
    _token: Annotated[TokenAuthContext, require_token],
    topics: list[str] = Query(
        default=[],
        description="The topic(s) to clear.",
    ),
    exclude_internal: bool = Query(
        default=True, description="Whether to exclude internal topics."
    ),
) -> None:
    """Clear messages from given topic(s).

    If no topics are specified, all topics will be cleared, except internal topics
    unless otherwise specified.

    Args:
    - `topics`: The topic(s) to clear.
    - `exclude_internal`: Whether to exclude internal topics.
    - `events_handler`: The events handler to use.

    Raises:
    - `HTTPException`: If an error occurs.
    """
    invalid_topics = [topic for topic in topics if not is_topic_valid(topic)]
    if invalid_topics:
        msg = f"Invalid topic(s): {', '.join(invalid_topics)}"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg
        )

    try:
        await events_handler.clear_topics(
            topics=topics, exclude_internal=exclude_internal
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)
        ) from err


@kafka_router.post(
    "/",
    operation_id="publish_event",
    summary="Publish the event provided in the request body to the given topic.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def publish_event(
    events_handler: dummies.EventsHandlerPortDummy,
    event_details: EventDetails,
    _token: Annotated[TokenAuthContext, require_token],
):
    """Publish the event provided in the request body to the given topic.

    Args:
    - `events_handler`: The events handler to use.

    Raises:
    - `HTTPException`: If an error occurs.
    """
    if not is_topic_valid(event_details.topic):
        msg = f"Invalid topic: {event_details.topic}"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg
        )

    try:
        await events_handler.publish_event(event_details=event_details)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)
        ) from err
