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

"""Integration tests for the Aggregator class"""

import pytest
from hexkit.providers.mongodb.testutils import MongoDbFixture

from dlqs.adapters.outbound.dao import get_aggregator
from tests.fixtures import utils
from tests.fixtures.config import get_config
from tests.fixtures.prepop import ReferenceEventsDict

pytestmark = pytest.mark.asyncio()


async def test_agg_on_empty_db(mongodb: MongoDbFixture):
    """Test that running the aggregator on an empty db returns an empty list."""
    config = get_config([mongodb.config])
    async with get_aggregator(config=config) as aggregator:
        results = await aggregator.aggregate(service="foo", topic="bar")
        assert results == []


async def test_aggregator(
    mongodb: MongoDbFixture, prepopped_events: ReferenceEventsDict
):
    """Test that the aggregator returns the correct results

    This test mimics the scenario where two services subscribe to the same topic
    and both services encounter errors with a series of events from that topic.
    For both services we insert a number of events in the DB, which have the same
    timestamp and other information (except for the event ID).
    """
    config = get_config([mongodb.config])
    async with get_aggregator(config=config) as aggregator:
        # Test aggregation with different skip and limit values (all valid)
        agg_params = [
            (0, None),
            (0, 5),
            (0, 25),
            (5, None),
            (5, 5),
            (5, 10),
            (5, 25),
        ]

        # Quick sanity check
        svc = utils.FSS
        topic = utils.USER_EVENTS
        assert svc in prepopped_events and topic in prepopped_events[svc]
        assert len(prepopped_events[utils.FSS][topic]) > 0

        # Run the aggregator with different valid parameters and compare to the reference
        for skip, limit in agg_params:
            agg_op = aggregator.aggregate(
                service=svc, topic=utils.USER_EVENTS, skip=skip, limit=limit
            )
            results = await agg_op
            end = skip + limit if limit else None
            expected = prepopped_events[svc][topic][skip:end]
            assert results == expected
