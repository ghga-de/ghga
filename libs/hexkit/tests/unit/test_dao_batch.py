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
#

"""Test the batch helpers of the DAO protocol.

They are synchronous, so they live apart from `test_dao.py`, which marks every test
as asyncio.
"""

import pytest

from hexkit.custom_types import ID
from hexkit.protocols.dao import (
    BatchOperationError,
    DaoError,
    ResourceNotFoundError,
    ensure_distinct_ids,
)


def test_batch_operation_error():
    """Test that BatchOperationError keeps the failures and the skipped IDs."""
    errors: dict[ID, DaoError] = {"a": ResourceNotFoundError(id_="a")}

    error = BatchOperationError(errors=errors, not_attempted=["b", "c"])

    assert error.errors == errors
    assert error.not_attempted == ("b", "c")
    assert str(error) == "1 resource(s) of the batch failed: ['a']"
    assert BatchOperationError(errors=errors).not_attempted == ()


def test_ensure_distinct_ids():
    """Test that ensure_distinct_ids names each repeated ID once."""
    ensure_distinct_ids(["a", "b", 1])
    ensure_distinct_ids([])

    with pytest.raises(ValueError, match=r"more than once: \['a', 1\]$"):
        ensure_distinct_ids(["a", 1, "b", "a", 1, "a"])
