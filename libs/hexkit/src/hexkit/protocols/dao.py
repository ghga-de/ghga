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

"""Protocol for creating Data Access Objects to perform CRUD (plus find) interactions
with the database.
"""

import typing
from abc import ABC, abstractmethod
from asyncio import sleep
from collections.abc import AsyncIterator, Awaitable, Callable, Collection, Mapping
from contextlib import AbstractAsyncContextManager
from functools import partial
from logging import Logger
from random import uniform
from types import TracebackType
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field

from hexkit.custom_types import ID
from hexkit.utils import FieldNotInModelError, validate_fields_in_model

__all__ = [
    "Dao",
    "DaoFactoryProtocol",
    "FindError",
    "FindResult",
    "MultipleHitsFoundError",
    "PreconditionFailedError",
    "ResourceAlreadyExistsError",
    "ResourceNotFoundError",
    "UUID4Field",
    "UniqueConstraintViolationError",
    "race_condition_retries",
]


class IndexBase(ABC):
    """Base from which all DAO index classes must inherit"""

    @abstractmethod
    def list_field_names(self) -> list[str]:
        """Returns a list of all fields specified by this index"""
        ...


# Type variable for handling Data Transfer Objects:
Dto = TypeVar("Dto", bound=BaseModel)
Index = TypeVar("Index", bound=IndexBase)


class DaoError(RuntimeError):
    """Base for all errors related to DAO operations."""


class ResourceNotFoundError(DaoError):
    """Raised when a requested resource did not exist."""

    def __init__(self, *, id_: ID):
        message = f'The resource with the id "{id_}" does not exist.'
        super().__init__(message)


class ResourceAlreadyExistsError(DaoError):
    """Raised when a resource did unexpectedly exist."""

    def __init__(self, *, id_: ID):
        message = f'The resource with the id "{id_}" already exists.'
        super().__init__(message)


class UniqueConstraintViolationError(DaoError):
    """Raised when attempting to insert a resource violated a uniqueness constraint.

    This does not apply to the default unique index automatically applied to
    the ID field.
    """

    def __init__(self, *, unique_fields: dict[str, Any]):
        message = (
            f"A resource with the unique field value(s) {unique_fields} already exists."
        )
        super().__init__(message)


class PreconditionFailedError(DaoError):
    """Raised when an update with `precondition` found the resource, but its
    current values didn't match the criteria.
    """

    def __init__(self, *, id_: ID, precondition: Mapping[str, Any]):
        message = (
            f'The resource with the id "{id_}" does not match the criteria'
            f" {precondition} for an atomic update."
        )
        super().__init__(message)


class FindError(DaoError):
    """Base for all error related to DAO find operations."""


class InvalidMappingError(FindError):
    """Raised when an invalid mapping was passed provided to find."""


class MultipleHitsFoundError(FindError):
    """Raised when a DAO find operation did result in multiple hits while only a
    single hit was expected.
    """

    def __init__(self, *, mapping: Mapping[str, str]):
        message = (
            "Multiple hits were found for the following key-value pairs while only a"
            f" single one was expected: {mapping}"
        )
        super().__init__(message)


class NoHitsFoundError(FindError):
    """Raised when a DAO find operation did result in no hits while a
    single hit was expected.
    """

    def __init__(self, *, mapping: Mapping[str, str]):
        message = (
            "No hits were found for the following key-value pairs while a single one"
            f" was expected: {mapping}"
        )
        super().__init__(message)


class DbTimeoutError(DaoError):
    """Raised when a database operation timed out."""

    def __init__(self, details: str):
        message = f"The database operation timed out: {details}"
        super().__init__(message)


# provide standardized default factory for UUID4 fields
UUID4Field = partial(Field, default_factory=uuid4)


class FindResult(AsyncIterator[Dto]):
    """An async-iterable result from find_all() that also exposes pagination metadata.

    The `total_count()` method performs an additional count query on first call (lazily)
    and caches the result for subsequent calls.
    """

    def __init__(
        self,
        *,
        results_iterator: AsyncIterator[Dto],
        get_total_count: Callable[[], Awaitable[int]],
    ) -> None:
        self._iterator = results_iterator
        self._get_total_count = get_total_count
        self._cached_total: int | None = None

    def __aiter__(self) -> "FindResult[Dto]":  # noqa: D105
        return self

    async def __anext__(self) -> Dto:  # noqa: D105
        return await self._iterator.__anext__()

    async def total_count(self) -> int:
        """Total number of matching documents, ignoring skip and limit.

        The result is cached after the first call.
        """
        if self._cached_total is None:
            self._cached_total = await self._get_total_count()
        return self._cached_total

    async def to_list(self) -> list[Dto]:
        """Collect all results into a list.

        Calling this function will consume the iterator. Subsequent cals will return
        an empty list.
        """
        return [item async for item in self]


class _RaceConditionAttempt:
    """A single try yielded by `race_condition_retries`.

    Used as a context manager: suppresses an `PreconditionFailedError` raised in its block,
    keeps it in `error`, and records whether the block finished without one.
    """

    def __init__(self) -> None:
        self.succeeded = False
        self.error: PreconditionFailedError | None = None

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if exc_type is None:
            self.succeeded = True
            return False
        if isinstance(exc_value, PreconditionFailedError):
            self.error = exc_value
            return True
        return False


async def race_condition_retries(  # noqa: PLR0913
    *,
    description: str,
    error_on_failure: BaseException,
    logger: Logger | None = None,
    max_tries: int = 3,
    interval: float = 0.5,
    jitter: float = 0.3,
) -> AsyncIterator[_RaceConditionAttempt]:
    """Yield attempts for an action that can lose a race condition.

    Wrap the action in `with attempt:` for each yielded attempt. Retries it up to
    `max_tries` times, waiting `interval` seconds (plus jitter) after each
    `PreconditionFailedError`. That error means the `precondition` of a DAO update no
    longer matched because another write came first. A `return` inside the block
    ends the retries.

    ```python
    async for attempt in race_condition_retries(
        description="update stats for box <box_id>",
        error_on_failure=error,
    ):
        with attempt:
            ...
    ```

    Args:
        description:
            What the action does, phrased to follow "to", e.g.
            "update stats for box <box_id>". Used in log messages.
        error_on_failure: The error to raise once all tries have failed.
        logger:
            Logs a debug message for each conflict and an error once all tries have
            failed. Nothing is logged if omitted.
        max_tries: How many times to try the action. Values below 1 count as 1.
        interval: Seconds to wait between tries. Negative values count as 0.
        jitter:
            Upper bound, in seconds, of a random delay added to each wait, so callers
            that conflicted don't retry at the same moment. Negative values count as 0.

    Raises:
    - `error_on_failure` if the action still raises `PreconditionFailedError` on the last try.
      It is chained from that last `PreconditionFailedError`.
    """
    description = description.strip(" .")
    tries = max(1, max_tries)
    last_error: PreconditionFailedError | None = None
    for attempt_number in range(1, tries + 1):
        attempt = _RaceConditionAttempt()
        yield attempt
        if attempt.succeeded:
            return
        last_error = attempt.error
        if logger:
            logger.debug("Detected race condition while trying to %s.", description)
        if attempt_number < tries:
            await sleep(max(0, interval) + uniform(0, max(jitter, 0)))  # noqa: S311

    if logger:
        logger.error(
            "Failed %s times to %s due to persistent race conditions.",
            tries,
            description,
        )
    raise error_on_failure from last_error


class Dao(typing.Protocol[Dto]):
    """A duck type with methods common to all DAOs."""

    @classmethod
    def with_transaction(cls) -> AbstractAsyncContextManager["Dao[Dto]"]:
        """Creates a transaction manager that uses an async context manager interface:

        Upon __aenter__, pens a new transactional scope. Returns a transaction-scoped
        DAO.

        Upon __aexit__, closes the transactional scope. A full rollback of the
        transaction is performed in case of an exception. Otherwise, the changes to the
        database are committed and flushed.
        """
        ...

    async def get_by_id(self, id_: ID) -> Dto:
        """Get a resource by providing its ID.

        Args:
            id_: The ID of the resource.

        Returns:
            The resource represented using the respective DTO model.

        Raises:
            ResourceNotFoundError: when resource with the specified id_ was not found
        """
        ...

    async def update(
        self, dto: Dto, *, precondition: Mapping[str, Any] | None = None
    ) -> None:
        """Update an existing resource.

        If `precondition` is supplied, the resource is only updated if its current
        values match them. The check and the update happen atomically.

        Args:
            dto:
                The updated resource content as a pydantic-based data transfer object
                including the resource ID.
            precondition:
                A mapping of field names to the values the existing resource must have.
                It does not need to contain the ID field, since that is implied.

        Raises:
            ResourceNotFoundError:
                when resource with the id specified in the dto was not found
            PreconditionFailedError:
                when the resource exists but doesn't match `precondition`
            InvalidMappingError: when `precondition` doesn't pass validation
            UniqueConstraintViolationError:
                when updating the dto would violate a unique index constraint over some
                field other than the ID field.
        """
        ...

    async def delete(self, id_: ID) -> None:
        """Delete a resource by providing its ID.

        Args:
            id_: The ID of the resource.

        Raises:
            ResourceNotFoundError: when resource with the specified id_ was not found
        """
        ...

    async def find_one(self, *, mapping: Mapping[str, Any]) -> Dto:
        """Find the resource that matches the specified mapping.

        It is expected that at most one resource matches the constraints.
        An exception is raised if no or multiple hits are found.

        The values in the mapping are used to filter the resources. Provide them
        using the same Python types as the corresponding DTO model fields, e.g. a
        UUID object for a UUID field and a datetime object for a datetime field.
        The behavior for non-scalar values depends on the specific provider.

        Args:
            mapping:
                A mapping where the keys correspond to the names of resource fields
                and the values correspond to the actual values of the resource fields

        Returns:
            Returns a hit in the form of the respective DTO model if exactly one hit
            was found that matches the given mapping.

        Raises:
            NoHitsFoundError:
                If no hit was found.
            MultipleHitsFoundError:
                Raised when obtaining more than one hit.
        """
        ...

    def find_all(
        self,
        *,
        mapping: Mapping[str, Any],
        skip: int | None = None,
        limit: int | None = None,
        sort: list[str] | None = None,
    ) -> "FindResult[Dto]":
        """Find all resources that match the specified mapping.

        The values in the mapping are used to filter the resources. Provide them
        using the same Python types as the corresponding DTO model fields, e.g. a
        UUID object for a UUID field and a datetime object for a datetime field.
        The behavior for non-scalar values depends on the specific provider.

        Args:
            mapping:
                A mapping where the keys correspond to the names of resource fields
                and the values correspond to the actual values of the resource fields.
            skip:
                Number of matching resources to skip before yielding results.
                Defaults to None (no skipping).
            limit:
                Maximum number of resources to yield. Defaults to None (no limit).
                Specifying 0 is interpreted literally and returns no results.
            sort:
                A list of field names defining the sort order, where field names
                prefixed with "-" indicate *descending* order. For example, if sort is
                specified as `["name", "-age"]`, the results would be sorted first by
                "name" in ascending order, then by "age" in descending order. When
                paginating with skip/limit, providing a sort order is strongly
                recommended to ensure consistent, deterministic results. Defaults to
                None (no sort).

        Returns:
            A FindResult that is async-iterable and also provides total_count().

        Raises:
            InvalidMappingError: If `mapping` doesn't pass validation.
            ValueError: if `skip` or `limit` are less than 0.
        """
        ...

    async def insert(self, dto: Dto) -> None:
        """Create a new resource.

        Args:
            dto:
                Resource content as a pydantic-based data transfer object including the
                resource ID.

        Raises:
            ResourceAlreadyExistsError:
                when a resource with the ID specified in the dto does already exist.
            UniqueConstraintViolationError:
                when inserting the dto would violate a unique index constraint over some
                field other than the ID field.
        """
        ...

    async def upsert(self, dto: Dto) -> None:
        """Update the provided resource if it already exists, create it otherwise.

        Args:
            dto:
                Resource content as a pydantic-based data transfer object including the
                resource ID.

        Raises:
            UniqueConstraintViolationError:
                when upserting the dto would violate a unique index constraint over some
                field other than the ID field.
        """
        ...


class DaoFactoryBase:
    """A base for Data Access Objects (DAO) Factory protocols."""

    class IdFieldNotFoundError(TypeError):
        """Raised when the dto_model did not contain the expected id_field."""

    class IdTypeNotSupportedError(TypeError):
        """Raised when the id_field of the dto_model has an unexpected Type."""

    class IndexFieldsInvalidError(ValueError):
        """Raised when providing an invalid list of fields to index."""

    @classmethod
    def _validate_dto_model_id(cls, *, dto_model: type[Dto], id_field: str) -> None:
        """Checks whether the dto_model contains the expected id_field.
        Raises IdFieldNotFoundError otherwise.
        """
        properties = dto_model.model_json_schema()["properties"]
        schema = properties.get(id_field)
        if schema is None:
            raise cls.IdFieldNotFoundError()
        id_type = schema.get("type")
        if id_type not in ("integer", "string"):
            raise cls.IdTypeNotSupportedError()

    @classmethod
    def _validate_fields_to_index(
        cls,
        *,
        dto_model: type[Dto],
        indexes: Collection[Index] | None,
    ) -> None:
        """Checks that all provided fields are present in the dto_model.
        Raises IndexFieldsInvalidError otherwise.
        """
        if not indexes:
            return

        try:
            for index in indexes:
                validate_fields_in_model(
                    model=dto_model, fields=index.list_field_names()
                )
        except FieldNotInModelError as error:
            raise cls.IndexFieldsInvalidError(
                f"Provided index fields are invalid: {error}"
            ) from error

    @classmethod
    def _validate(
        cls,
        *,
        dto_model: type[Dto],
        id_field: str,
        indexes: Collection[Index] | None,
    ) -> None:
        """Validates the input parameters of the get_dao method."""
        cls._validate_dto_model_id(dto_model=dto_model, id_field=id_field)
        cls._validate_fields_to_index(dto_model=dto_model, indexes=indexes)


class DaoFactoryProtocol(DaoFactoryBase, ABC, Generic[Index]):
    """A protocol describing a factory to produce Data Access Objects (DAO) objects
    that are enclosed in transactional scopes.
    """

    async def get_dao(
        self,
        *,
        name: str,
        dto_model: type[Dto],
        id_field: str,
        indexes: Collection[Index] | None = None,
    ) -> Dao[Dto]:
        """Constructs a DAO for interacting with resources in a database.

        Args:
            name:
                The name of the resource type (roughly equivalent to the name of a
                database table or collection).
            dto_model:
                A DTO (Data Transfer Object) model describing the shape of resources.
            id_field:
                The name of the field of the `dto_model` that serves as resource ID.
                (DAO implementation might use this field as primary key.)
            indexes:
                Optionally, provide any indexes that should be created in addition to
                the provider's default index on `id_field`. Defaults to None.
        Returns:
            A DAO specific to the provided DTO model.

        Raises:
            self.IdFieldNotFoundError:
                Raised when the dto_model did not contain the expected id_field.
            self.IdTypeNotSupportedError:
                Raised when the id_field of the dto_model has an unexpected type.
        """
        self._validate(dto_model=dto_model, id_field=id_field, indexes=indexes)

        return await self._get_dao(
            name=name,
            dto_model=dto_model,
            id_field=id_field,
            indexes=indexes,
        )

    @abstractmethod
    async def _get_dao(
        self,
        *,
        name: str,
        dto_model: type[Dto],
        id_field: str,
        indexes: Collection[Index] | None,
    ) -> Dao[Dto]:
        """*To be implemented by the provider. Input validation is done outside of this
        method.*
        """
        ...
