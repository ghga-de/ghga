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
    DbTimeoutError,
    ResourceAlreadyExistsError,
    UniqueConstraintViolationError,
)
from hexkit.providers.mongodb.provider.dao import (
    DUPLICATE_KEY_ERROR,
    MAX_TIME_MS_EXPIRED,
    _errors_from_bulk_write,
)

IDS = ["a", "b", "c", "d"]


def bulk_write_error(
    *write_errors: dict[str, Any], concern: dict[str, Any] | None = None
):
    """Build a BulkWriteError with the given write errors, as pymongo reports them."""
    details = {
        "writeErrors": list(write_errors),
        "writeConcernErrors": [concern] if concern else [],
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


def test_write_past_its_time_limit():
    """Test that a write that ran out of its maxTimeMS maps to a timeout."""
    failure = {"index": 2, "code": MAX_TIME_MS_EXPIRED, "errmsg": "time limit"}

    error = _errors_from_bulk_write(bulk_write_error(failure), IDS, ordered=False)

    assert type(error.errors["c"]) is DbTimeoutError


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


WRITE_CONCERN_ERROR = {"code": 64, "errmsg": "waiting timed out"}
WRITE_CONCERN_TIMEOUT = WRITE_CONCERN_ERROR | {"errInfo": {"wtimeout": True}}


@pytest.mark.parametrize(
    "concern, expected",
    [
        (WRITE_CONCERN_ERROR, DaoError),
        (WRITE_CONCERN_TIMEOUT, DbTimeoutError),
        ({"code": MAX_TIME_MS_EXPIRED, "errmsg": "waiting timed out"}, DbTimeoutError),
    ],
)
def test_write_concern_error_names_unconfirmed_resources(
    concern: dict[str, Any], expected: type[DaoError]
):
    """Test that a write concern error names each attempted resource without a
    write error of its own, with the error its single write raises.

    The error carries the write concern's own message, not the whole bulk result.
    """
    error = _errors_from_bulk_write(
        bulk_write_error(duplicate_key(1, {"_id": "b"}), concern=concern),
        IDS,
        ordered=False,
    )

    assert type(error.errors["b"]) is ResourceAlreadyExistsError
    for id_ in ["a", "c", "d"]:
        assert type(error.errors[id_]) is expected
        assert str(error.errors[id_]).endswith("waiting timed out")
    assert error.not_attempted == ()


def test_write_concern_error_in_ordered_batch():
    """Test that an ordered batch names only the attempted resources with the write
    concern error and still lists the skipped ones.
    """
    error = _errors_from_bulk_write(
        bulk_write_error(duplicate_key(1, {"_id": "b"}), concern=WRITE_CONCERN_TIMEOUT),
        IDS,
        ordered=True,
    )

    assert list(error.errors) == ["b", "a"]
    assert type(error.errors["a"]) is DbTimeoutError
    assert error.not_attempted == ("c", "d")


@pytest.mark.parametrize("ordered", [False, True])
def test_write_concern_error_alone_names_every_resource(ordered: bool):
    """Test that a write concern error without any write error names every resource."""
    error = _errors_from_bulk_write(
        bulk_write_error(concern=WRITE_CONCERN_TIMEOUT), IDS, ordered=ordered
    )

    assert list(error.errors) == IDS
    assert all(type(failure) is DbTimeoutError for failure in error.errors.values())
    assert error.not_attempted == ()


def test_write_time_limit_does_not_make_write_concern_a_timeout():
    """Test that a write error that ran out of its maxTimeMS leaves a write concern
    error that is no timeout a plain DaoError.
    """
    failure = {"index": 2, "code": MAX_TIME_MS_EXPIRED, "errmsg": "time limit"}

    error = _errors_from_bulk_write(
        bulk_write_error(failure, concern=WRITE_CONCERN_ERROR), IDS, ordered=False
    )

    assert type(error.errors["c"]) is DbTimeoutError
    for id_ in ["a", "b", "d"]:
        assert type(error.errors[id_]) is DaoError


@pytest.mark.parametrize(
    "concerns, expected",
    [
        ([WRITE_CONCERN_TIMEOUT, WRITE_CONCERN_ERROR], DaoError),
        ([WRITE_CONCERN_ERROR, WRITE_CONCERN_TIMEOUT], DbTimeoutError),
    ],
)
def test_last_write_concern_error_decides(
    concerns: list[dict[str, Any]], expected: type[DaoError]
):
    """Test that of several write concern errors only the last one counts, as for
    pymongo.
    """
    bulk_error = bulk_write_error()
    bulk_error.details["writeConcernErrors"] = concerns

    error = _errors_from_bulk_write(bulk_error, IDS, ordered=False)

    assert all(type(failure) is expected for failure in error.errors.values())
