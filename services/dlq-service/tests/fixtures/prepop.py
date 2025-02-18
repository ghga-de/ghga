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

"""Fixture to pre-populate the database with some test DLQ events"""

from datetime import datetime, timedelta
from functools import partial
from random import choice

import pytest
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.providers.mongodb.provider import dto_to_document
from hexkit.providers.mongodb.testutils import MongoDbFixture

from dlqs.adapters.outbound.dao import DLQ_EVENTS_COLLECTION
from dlqs.models import StoredDLQEvent
from tests.fixtures import utils

ReferenceEventsDict = dict[str, dict[str, list[StoredDLQEvent]]]


def get_event_func(service: str, topic: str):
    """Get the event creation function from utils.py for the given service and topic"""
    if service in (utils.UFS, utils.FSS):
        match topic:
            case utils.NOTIFICATIONS:
                return utils.notifications_event
            case utils.GRAPH_UPDATES:
                return utils.graph_event
            case utils.USER_EVENTS:
                return partial(utils.user_event, service=service)  # type: ignore
            case _:
                pass
    raise ValueError(
        f"Service/topic not recognized for pre-pop fixture: {service}/{topic}"
    )


def generate_db_events(n: int, service: str, topic: str) -> list[StoredDLQEvent]:
    """Generate a list of events with unique timestamps/event IDs sorted by timestamp

    Event with timestamps[0] is the oldest event / first to be processed.
    """
    now = now_as_utc()
    timestamps: list[datetime] = [now - timedelta(hours=n - i) for i in range(n)]
    event_func = get_event_func(service, topic)
    db_events = []
    for i, timestamp in enumerate(timestamps):
        raw_event = event_func(offset=i)
        db_event = utils.dlq_to_db(raw_event)
        db_event.timestamp = timestamp
        db_events.append(db_event)
    return db_events


@pytest.fixture(name="prepopped_events", scope="function")
def populate_db(mongodb: MongoDbFixture) -> ReferenceEventsDict:
    """Populate the database with some test DLQ events for each service/topic.

    The return value is a dictionary containing the inserted events sorted by time in
    order to more conveniently verify the results of the tests.
    """
    count = 10
    notifications = generate_db_events(count, utils.UFS, utils.NOTIFICATIONS)
    graph_updates = generate_db_events(count, utils.FSS, utils.GRAPH_UPDATES)
    ufs_user_events = generate_db_events(count, utils.UFS, utils.USER_EVENTS)
    fss_user_events = generate_db_events(count, utils.FSS, utils.USER_EVENTS)
    events = notifications + graph_updates + ufs_user_events + fss_user_events

    reference: ReferenceEventsDict = {
        utils.UFS: {
            utils.NOTIFICATIONS: notifications,
            utils.USER_EVENTS: ufs_user_events,
        },
        utils.FSS: {
            utils.GRAPH_UPDATES: graph_updates,
            utils.USER_EVENTS: fss_user_events,
        },
    }

    # insert into the DB in a random order, and store in reference dict
    db_name = mongodb.config.db_name
    coll = mongodb.client[db_name][DLQ_EVENTS_COLLECTION]
    while events:
        i = choice(range(len(events)))
        event = events[i]
        db_event = event.model_copy(deep=True)
        doc = dto_to_document(db_event, id_field="dlq_id")
        coll.insert_one(doc)
        del events[i]

    return reference
