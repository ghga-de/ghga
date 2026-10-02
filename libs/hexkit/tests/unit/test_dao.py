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

"""Testing the DAO factory protocol."""

import warnings
from collections.abc import Collection
from dataclasses import dataclass

import pytest
from pydantic import UUID4, BaseModel
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from hexkit.protocols.dao import (
    MAPPING_DEPRECATION_MESSAGE,
    Dao,
    DaoError,
    DaoFactoryProtocol,
    DbTimeoutError,
    Dto,
    IndexBase,
    MultipleHitsFoundError,
    NoHitsFoundError,
    UUID4Field,
)
from hexkit.providers.mongodb import (
    MongoDbConfig,
    MongoDbDaoFactory,
    translate_pymongo_errors,
)
from hexkit.providers.testing import new_mock_dao_class

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


# TODO: Remove `mapping` when moving hexkit to v11.0.0
class MappingDto(BaseModel):
    """A model for exercising the `mapping` deprecation."""

    id: UUID4 = UUID4Field()
    count: int = 0


# TODO: Remove `mapping` when moving hexkit to v11.0.0
@pytest.mark.parametrize("method", ["find_one", "find_all"])
async def test_mapping_is_deprecated_alias_for_filter(method: str):
    """Test that find methods accept `mapping` but warn, and that `filter_` is quiet."""
    dao = new_mock_dao_class(dto_model=MappingDto, id_field="id")()
    item = MappingDto(count=1)
    await dao.insert(item)

    async def call(**kwargs) -> list[MappingDto]:
        if method == "find_one":
            return [await dao.find_one(**kwargs)]
        return [dto async for dto in dao.find_all(**kwargs)]

    with pytest.deprecated_call(match=MAPPING_DEPRECATION_MESSAGE):
        assert await call(mapping={"count": 1}) == [item]

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert await call(filter_={"count": 1}) == [item]

    with pytest.raises(TypeError, match="not both"):
        await call(filter_={"count": 1}, mapping={"count": 1})

    with pytest.raises(TypeError, match="filter_"):
        await call()


# TODO: Remove `mapping` when moving hexkit to v11.0.0
@pytest.mark.parametrize("error", [NoHitsFoundError, MultipleHitsFoundError])
async def test_find_errors_accept_deprecated_mapping(
    error: type[NoHitsFoundError] | type[MultipleHitsFoundError],
):
    """Test that the find errors accept `mapping` but warn, and render `filter_`."""
    with pytest.deprecated_call(match=MAPPING_DEPRECATION_MESSAGE):
        from_mapping = error(mapping={"count": "1"})

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        from_filter = error(filter_={"count": "1"})

    assert str(from_mapping) == str(from_filter)
    assert "{'count': '1'}" in str(from_filter)
