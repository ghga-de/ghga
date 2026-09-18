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

"""Testing the DAO protocol module."""

import logging
from collections.abc import Collection
from dataclasses import dataclass
from typing import Any

import pytest
from pydantic import UUID4, BaseModel
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from hexkit.protocols.dao import (
    Dao,
    DaoError,
    DaoFactoryProtocol,
    DbTimeoutError,
    Dto,
    IndexBase,
    PreconditionFailedError,
    ResourceNotFoundError,
    UUID4Field,
    race_condition_retries,
)
from hexkit.providers.mongodb import (
    MongoDbConfig,
    MongoDbDaoFactory,
    translate_pymongo_errors,
)

pytestmark = pytest.mark.asyncio()


@dataclass
class FakeIndex(IndexBase):
    """A index for testing with the FakeDaoFactory"""

    fields: Collection[str]

    def list_field_names(self) -> list[str]:
        """Return all the fields in this 'index'"""
        return list(self.fields)


class FakeDaoFactory(DaoFactoryProtocol[FakeIndex]):
    """Implements the DaoFactoryProtocol without providing any logic."""

    async def _get_dao(
        self,
        *,
        name: str,
        dto_model: type[Dto],
        id_field: str,
        indexes: Collection[FakeIndex] | None,
    ) -> Dao[Dto]:
        """*To be implemented by the provider. Input validation is done outside of this
        method.*
        """
        raise NotImplementedError()


class ExampleDto(BaseModel):
    """Example DTO model."""

    id: UUID4 = UUID4Field(description="The ID of the resource.")
    str_field: str
    int_field: int
    bool_field: bool


async def test_get_dto_valid():
    """Use the get_dao method of the DaoFactory with valid parameters."""
    dao_factory = FakeDaoFactory()

    for id_field in "id", "str_field", "int_field":
        # should raise a NotImplementedError because ._get_dao() is not implemented,
        # but the parameters should be considered valid
        with pytest.raises(NotImplementedError):
            _ = await dao_factory.get_dao(
                name="test_dao",
                dto_model=ExampleDto,
                id_field=id_field,
                indexes=[FakeIndex(fields={"str_field", "int_field"})],
            )


async def test_get_dto_invalid_id():
    """Use the get_dao method of the DaoFactory with an invalid ID that is not found in
    the provided DTO model or has the wrong type.
    """
    dao_factory = FakeDaoFactory()

    with pytest.raises(DaoFactoryProtocol.IdFieldNotFoundError):
        _ = await dao_factory.get_dao(
            name="test_dao", dto_model=ExampleDto, id_field="non_existing_field"
        )

    with pytest.raises(DaoFactoryProtocol.IdTypeNotSupportedError):
        _ = await dao_factory.get_dao(
            name="test_dao", dto_model=ExampleDto, id_field="bool_field"
        )


async def test_get_dto_invalid_fields_to_index():
    """Use the get_dao method of the DaoFactory with an invalid list of fields to index."""
    dao_factory = FakeDaoFactory()

    with pytest.raises(DaoFactoryProtocol.IndexFieldsInvalidError):
        _ = await dao_factory.get_dao(
            name="test_dao",
            dto_model=ExampleDto,
            id_field="id",
            indexes=[FakeIndex(fields={"str_field", "non_existing_field"})],
        )


async def test_mongodb_timeout():
    """Test the timeout functionality by pointing towards a non-existent DB."""
    config = MongoDbConfig(
        mongo_timeout=1,
        mongo_dsn="mongodb://localhost:27017",
        db_name="test",
    )

    async with MongoDbDaoFactory.construct(config=config) as dao_factory:
        dao = await dao_factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
        )

        resource = ExampleDto(bool_field=True, int_field=42, str_field="test")

        with pytest.raises(DbTimeoutError):
            await dao.insert(resource)

        with pytest.raises(DbTimeoutError):
            await dao.get_by_id(resource.id)

        with pytest.raises(DbTimeoutError):
            await dao.find_one(mapping={"id": str(resource.id)})

        with pytest.raises(DbTimeoutError):
            [hit async for hit in dao.find_all(mapping={})]

        with pytest.raises(DbTimeoutError):
            await dao.update(resource)

        with pytest.raises(DbTimeoutError):
            await dao.upsert(resource)

        with pytest.raises(DbTimeoutError):
            await dao.delete(resource.id)


async def test_db_timeout_error_translator():
    """Test the function that translates a DB timeout error to a generic error."""
    timeout_error = ServerSelectionTimeoutError()  # .timeout returns True
    not_timeout_error = PyMongoError()  # .timeout is False by default

    # Non-timeout errors should be translated to DaoError
    with pytest.raises(DaoError):
        with translate_pymongo_errors():
            raise not_timeout_error

    # Timeout-caused PyMongoError instances should be translated to DbTimeoutError
    with pytest.raises(DbTimeoutError):
        with translate_pymongo_errors():
            raise timeout_error

    # Since the function only catches PyMongoError instances, test other exceptions
    with pytest.raises(ValueError):
        with translate_pymongo_errors():
            raise ValueError()


class GaveUpError(RuntimeError):
    """Passed as `error_on_failure` to `race_condition_retries` in tests."""


class ConflictingUpdate:
    """An update that loses a race condition on its first `conflicts` tries."""

    def __init__(self, *, conflicts: int):
        self.conflicts = conflicts
        self.tries = 0

    async def run(self, **retry_kwargs: Any) -> None:
        """Run the update with `race_condition_retries`."""
        async for attempt in race_condition_retries(
            description="update the resource",
            error_on_failure=GaveUpError(),
            **retry_kwargs,
        ):
            with attempt:
                self.tries += 1
                if self.tries <= self.conflicts:
                    raise PreconditionFailedError(
                        id_="test", precondition={"try": self.tries}
                    )


@pytest.fixture()
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Replace the `sleep` used by `race_condition_retries` with one that only records
    the requested waits.
    """
    waits: list[float] = []

    async def record_sleep(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr("hexkit.protocols.dao.sleep", record_sleep)
    return waits


@pytest.mark.parametrize("conflicts", [0, 1, 2])
async def test_race_condition_retries_until_success(
    conflicts: int, sleeps: list[float]
):
    """Test that the action is retried after each conflict until it succeeds, waiting
    between `interval` and `interval + jitter` seconds each time.
    """
    update = ConflictingUpdate(conflicts=conflicts)
    await update.run(max_tries=3, interval=0.5, jitter=0.3)

    assert update.tries == conflicts + 1
    assert len(sleeps) == conflicts
    assert all(0.5 <= wait <= 0.8 for wait in sleeps)


async def test_race_condition_retries_exhausted(
    sleeps: list[float], caplog: pytest.LogCaptureFixture
):
    """Test that `error_on_failure` is raised after the last try, chained from the
    `PreconditionFailedError`, without waiting after that try.
    """
    logger_name = "hexkit.tests.race_condition_retries"
    caplog.set_level(logging.DEBUG, logger=logger_name)
    update = ConflictingUpdate(conflicts=5)

    with pytest.raises(GaveUpError) as exc_info:
        await update.run(max_tries=3, logger=logging.getLogger(logger_name))

    assert update.tries == 3
    assert len(sleeps) == 2
    assert isinstance(exc_info.value.__cause__, PreconditionFailedError)
    assert [record.levelname for record in caplog.records] == [
        "DEBUG",
        "DEBUG",
        "DEBUG",
        "ERROR",
    ]
    assert "Failed 3 times to update the resource" in caplog.records[-1].getMessage()


@pytest.mark.parametrize("max_tries", [0, -1])
async def test_race_condition_retries_tries_at_least_once(
    max_tries: int, sleeps: list[float]
):
    """Test that the action is tried once when `max_tries` is below 1."""
    update = ConflictingUpdate(conflicts=1)

    with pytest.raises(GaveUpError):
        await update.run(max_tries=max_tries)

    assert update.tries == 1
    assert not sleeps


async def test_race_condition_retries_return_ends_retries():
    """Test that a `return` inside the block ends the retries."""

    async def update_if_changed() -> str:
        async for attempt in race_condition_retries(
            description="update the resource", error_on_failure=GaveUpError()
        ):
            with attempt:
                return "unchanged"
        return "retries ended without a return"

    assert await update_if_changed() == "unchanged"


async def test_race_condition_retries_other_errors():
    """Test that errors other than `PreconditionFailedError` are raised without a retry."""
    tries = 0

    with pytest.raises(ResourceNotFoundError):
        async for attempt in race_condition_retries(
            description="update the resource", error_on_failure=GaveUpError()
        ):
            with attempt:
                tries += 1
                raise ResourceNotFoundError(id_="test")

    assert tries == 1
