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

"""Unit tests for the Aggregator class"""

from unittest.mock import AsyncMock, Mock

import pytest
from pymongo.errors import OperationFailure

from dlqs.adapters.outbound.dao import Aggregator


@pytest.mark.parametrize("err_on_find_one", [True, False])
@pytest.mark.asyncio
async def test_db_error_handling(err_on_find_one: bool):
    """Test that the Aggregator translates Pymongo errors correctly.

    Both `aggregate` and `find_one` methods are mocked to raise an `OperationFailure`.
    """
    mock_collection = Mock()
    mock_collection.aggregate.side_effect = OperationFailure("Something went wrong")
    mock_collection.find_one = AsyncMock()
    if err_on_find_one:
        mock_collection.find_one.side_effect = OperationFailure("Something went wrong")
    else:
        mock_collection.find_one.return_value = [1]  # just something to let code pass

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
