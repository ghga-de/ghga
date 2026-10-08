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

"""Test how the MongoDB provider maps bulk write errors to the errors of a batch."""

from typing import Any

import pytest
from pymongo.errors import BulkWriteError

from hexkit.protocols.dao import (
    DaoError,
    ResourceAlreadyExistsError,
    UniqueConstraintViolationError,
)
from hexkit.providers.mongodb.provider.dao import (
    DUPLICATE_KEY_ERROR,
    _errors_from_bulk_write,
)

IDS = ["a", "b", "c", "d"]


def bulk_write_error(*write_errors: dict[str, Any], concern: bool = False):
    """Build a BulkWriteError with the given write errors, as pymongo reports them."""
    details = {
        "writeErrors": list(write_errors),
        "writeConcernErrors": [{"code": 64, "errmsg": "waiting timed out"}]
        if concern
        else [],
        "nInserted": 0,
        "nMatched": 0,
    }
    return BulkWriteError(details)


def duplicate_key(index: int, key_value: dict[str, Any] | None) -> dict[str, Any]:
    """A write error for a duplicate key at the given position of the batch."""
    failure = {"index": index, "code": DUPLICATE_KEY_ERROR, "errmsg": "E11000"}
    if key_value is not None:
        failure["keyValue"] = key_value
    return failure


@pytest.mark.parametrize(
    "key_value, expected",
    [
        ({"_id": "b"}, ResourceAlreadyExistsError),
        (None, ResourceAlreadyExistsError),
        ({"field_a": "x"}, UniqueConstraintViolationError),
        ({"_id": "b", "field_a": "x"}, UniqueConstraintViolationError),
    ],
)
def test_duplicate_keys(key_value: dict[str, Any] | None, expected: type[DaoError]):
    """Test that a duplicate key maps to the error of the index that clashed."""
    error = _errors_from_bulk_write(
        bulk_write_error(duplicate_key(1, key_value)), IDS, ordered=False
    )

    assert list(error.errors) == ["b"]
    assert type(error.errors["b"]) is expected
    assert error.not_attempted == ()


def test_other_write_error():
    """Test that any other write error keeps the server's message."""
    failure = {"index": 2, "code": 121, "errmsg": "Document failed validation"}

    error = _errors_from_bulk_write(bulk_write_error(failure), IDS, ordered=False)

    assert type(error.errors["c"]) is DaoError
    assert str(error.errors["c"]) == "Document failed validation"


def test_unordered_collects_every_failure():
    """Test that an unordered batch reports all failures and skips nothing."""
    error = _errors_from_bulk_write(
        bulk_write_error(duplicate_key(0, {"_id": "a"}), duplicate_key(3, None)),
        IDS,
        ordered=False,
    )

    assert list(error.errors) == ["a", "d"]
    assert error.not_attempted == ()


def test_ordered_lists_skipped_ids():
    """Test that an ordered batch lists the IDs after its failure as not attempted."""
    error = _errors_from_bulk_write(
        bulk_write_error(duplicate_key(1, {"_id": "b"})), IDS, ordered=True
    )

    assert list(error.errors) == ["b"]
    assert error.not_attempted == ("c", "d")


def test_write_concern_error_fails_the_call():
    """Test that a write concern error, which no resource caused, fails the call."""
    with pytest.raises(DaoError, match="waiting timed out"):
        _errors_from_bulk_write(bulk_write_error(concern=True), IDS, ordered=False)
