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


def test_batch_operation_error_names_five():
    """Test that the message names five failed IDs and a note lists all of them."""
    ids = list("abcdefg")
    errors: dict[ID, DaoError] = {id_: ResourceNotFoundError(id_=id_) for id_ in ids}

    error = BatchOperationError(errors=errors)

    assert str(error) == (
        "7 resource(s) of the batch failed: ['a', 'b', 'c', 'd', 'e'] and 2 more"
    )
    assert error.__notes__ == [f"All 7 IDs: {ids}"]
    assert len(error.errors) == 7

    five = BatchOperationError(errors=dict(list(errors.items())[:5]))
    assert str(five).endswith("['a', 'b', 'c', 'd', 'e']")
    assert not hasattr(five, "__notes__")


def test_ensure_distinct_ids():
    """Test that ensure_distinct_ids names each repeated ID once."""
    ensure_distinct_ids(["a", "b", 1])
    ensure_distinct_ids([])

    with pytest.raises(ValueError, match=r"more than once: \['a', 1\]$") as info:
        ensure_distinct_ids(["a", 1, "b", "a", 1, "a"])
    assert not hasattr(info.value, "__notes__")


def test_ensure_distinct_ids_names_five():
    """Test that the message names five repeated IDs and a note lists all of them."""
    repeated = list("abcdefg")

    with pytest.raises(ValueError) as info:
        ensure_distinct_ids(repeated * 2)

    assert str(info.value).endswith("['a', 'b', 'c', 'd', 'e'] and 2 more")
    assert info.value.__notes__ == [f"All 7 IDs: {repeated}"]
