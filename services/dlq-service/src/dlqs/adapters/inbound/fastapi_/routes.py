# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""FastAPI endpoint function definitions"""

from typing import Annotated

from fastapi import APIRouter, Body, status
from pydantic import UUID4

from dlqs import models
from dlqs.adapters.inbound.fastapi_.dummies import DLQManagerDummy
from dlqs.adapters.inbound.fastapi_.http_authorization import (
    TokenAuthContext,
    require_token,
)
from dlqs.adapters.inbound.fastapi_.http_exceptions import (
    HttpEmptyDLQError,
    HttpInternalServerError,
    HttpOverrideValidationError,
    HttpPreviewParamsError,
    HttpSequenceError,
)
from dlqs.ports.inbound.dlq_manager import DLQManagerPort

router = APIRouter()

RESPONSES = {
    "internalServerError": {"model": HttpInternalServerError.get_body_model()},
    "previewParamsError": {"model": HttpPreviewParamsError.get_body_model()},
    "overrideValidationError": {"model": HttpOverrideValidationError.get_body_model()},
    "emptyDLQError": {"model": HttpEmptyDLQError.get_body_model()},
    "dlqSequenceError": {"model": HttpSequenceError.get_body_model()},
}


@router.get(
    "/health",
    summary="health",
    status_code=status.HTTP_200_OK,
)
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


@router.get(
    "/{service}/{topic}",
    summary="Return the next events in the topic",
    status_code=status.HTTP_200_OK,
    response_model=list[models.StoredDLQEvent],
    responses={
        status.HTTP_400_BAD_REQUEST: RESPONSES["previewParamsError"],
        status.HTTP_500_INTERNAL_SERVER_ERROR: RESPONSES["internalServerError"],
    },
)
async def get_events(
    dlq_manager: DLQManagerDummy,
    _token: Annotated[TokenAuthContext, require_token],
    service: str,
    topic: str,
    skip: int = 0,
    limit: int | None = None,
) -> list[models.StoredDLQEvent]:
    """Return the next events in the topic.

    This is a preview of the events and does not impact event ordering within the DLQ.
    """
    try:
        return await dlq_manager.preview_events(
            service=service, topic=topic, limit=limit, skip=skip
        )
    except ValueError as err:
        raise HttpPreviewParamsError(skip=skip, limit=limit) from err
    except Exception as exc:
        # DLQPreviewError and all others get caught here
        raise HttpInternalServerError() from exc


@router.post(
    "/{service}/{topic}",
    summary="Process and publish the next event in the topic for the given service.",
    description=(
        "Returns the published event data or, if dry_run is True, the event"
        + " that would have been published."
    ),
    status_code=status.HTTP_200_OK,
    response_model=models.PublishableEventData,
    responses={
        status.HTTP_400_BAD_REQUEST: RESPONSES["overrideValidationError"],
        status.HTTP_404_NOT_FOUND: RESPONSES["emptyDLQError"],
        status.HTTP_409_CONFLICT: RESPONSES["dlqSequenceError"],
        status.HTTP_500_INTERNAL_SERVER_ERROR: RESPONSES["internalServerError"],
    },
)
async def process_event(  # noqa: PLR0913
    service: str,
    topic: str,
    dlq_manager: DLQManagerDummy,
    _token: Annotated[TokenAuthContext, require_token],
    dlq_id: UUID4 = Body(..., description="The DLQ ID of the event to process."),
    override: models.EventCore | None = None,
    dry_run: bool = False,
) -> models.PublishableEventData:
    """Process the next event in the topic, optionally publishing the supplied event.

    Returns the published event data or, if dry_run is True, the event that would have
    been published.
    """
    try:
        return await dlq_manager.process_event(
            service=service,
            topic=topic,
            dlq_id=dlq_id,
            override=override,
            dry_run=dry_run,
        )
    except DLQManagerPort.DLQSequenceError as err:
        raise HttpSequenceError(service=service, topic=topic, dlq_id=dlq_id) from err
    except DLQManagerPort.DLQEmptyError as err:
        raise HttpEmptyDLQError(service=service, topic=topic) from err
    except DLQManagerPort.DLQValidationError as err:
        raise HttpOverrideValidationError(event=override, reason=str(err)) from err
    except Exception as exc:
        # lump all other errors here
        raise HttpInternalServerError() from exc


@router.delete(
    "/{dlq_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Discard the event with the given DLQ ID, if it exists.",
    responses={status.HTTP_500_INTERNAL_SERVER_ERROR: RESPONSES["internalServerError"]},
)
async def discard_event(
    dlq_id: UUID4,
    dlq_manager: DLQManagerDummy,
    _token: Annotated[TokenAuthContext, require_token],
) -> None:
    """Discard the event with the given DLQ ID, if it exists."""
    try:
        return await dlq_manager.discard_event(dlq_id=dlq_id)
    except Exception as exc:
        # lump all other errors here
        raise HttpInternalServerError() from exc
