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

"""Unit tests for the Aggregator class"""

from unittest.mock import Mock

import pytest
from pymongo.errors import OperationFailure

from dlqs.adapters.outbound.dao import Aggregator


@pytest.mark.asyncio
async def test_db_error_handling():
    """Test that the Aggregator translates Pymongo errors correctly.

    The collection methods are mocked to raise an `OperationFailure`.
    """
    mock_collection = Mock()
    mock_collection.find.side_effect = OperationFailure("Something went wrong")

    aggregator = Aggregator(collection=mock_collection)
    with pytest.raises(Aggregator.AggregationError):
        await aggregator.aggregate(service="test", topic="test", skip=0, limit=10)


@pytest.mark.asyncio
async def test_bad_params():
    """Test that the Aggregator raises an error if bad params are supplied."""
    mock_collection = Mock()
    aggregator = Aggregator(collection=mock_collection)
    with pytest.raises(ValueError):
        await aggregator.aggregate(service="test", topic="test", skip=-1, limit=10)
    with pytest.raises(ValueError):
        await aggregator.aggregate(service="test", topic="test", skip=0, limit=-1)
    with pytest.raises(ValueError):
        await aggregator.aggregate(service="test", topic="test", skip=0, limit=0)
