# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""This module provides functionality for working with exception mappings.

A exception mapping is a datastructure that maps an HTTP error response (4xx or 5xx)
to a python exception.
"""

import inspect
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple, Optional, cast

from ghga_service_commons.httpyexpect.client.custom_types import (
    ExceptionFactory,
    ExceptionFactoryParam,
    ExceptionId,
    ExceptionMappingSpec,
)
from ghga_service_commons.httpyexpect.client.exceptions import UnexpectedError
from ghga_service_commons.httpyexpect.validation import (
    ValidationError,
    assert_error_code,
    validate_exception_id,
)

EXCEPTION_FACTORY_PARAMS = ("status_code", "exception_id", "description", "data")


class FactoryKit(NamedTuple):
    """A container for an exception factory.

    Also includes instruction on which parameters are required.
    """

    factory: ExceptionFactory
    required_params: Sequence[ExceptionFactoryParam]


class ExceptionMapping:
    """A datastructure that maps an HTTP response (4xx or 5xx) to a python exception.

    It will except a dict-based specification defining the mapping as input.
    This spec will be validated and public methods and public methods will be exposes
    that simplify the interaction with the encoded exception mapping.
    """

    def __init__(
        self,
        spec: ExceptionMappingSpec,
        *,
        fallback_factory: ExceptionFactory = UnexpectedError,
    ):
        """
        Initialize with a dict-based specification of a exception mappings.

        Args:
            spec:
                A dict-based specification defining the mapping between status codes
                plus exception IDs on the one hand and python exceptions on the other.
            fallback_factory:
                An exception factory used when no matches where found using the spec.

        Raises:
            ValidationError: If the provided spec or fallback_factory are invalid.
        """
        self._spec: Any = spec
        self._fallback_factory = fallback_factory

        self._validate(self._spec)
        try:
            self._check_exception_factory(fallback_factory)
        except ValidationError as error:
            raise ValidationError("Invalid fallback factory.") from error

    @staticmethod
    def _check_exception_id_mapping(
        exc_id_mapping: object,
        *,
        status_code: int,
    ) -> None:
        """Validate exception id mapping.

        Check that the exception id mapping provided per status code is a valid python
        Mapping.
        """
        if not isinstance(exc_id_mapping, Mapping):
            raise ValidationError(
                f"The mapping provided for the {status_code} status code was not a"
                + " dict (or python Mapping-compatible datastructure)."
            )

    @staticmethod
    def _get_error_intro(
        status_code: Optional[int] = None, exception_id: Optional[str] = None
    ):
        """Return an intro for a ValidationError.

        To be used only by the `inspect_factory_params` and the `check_exception_factory`
        functions.
        """
        return (
            (
                "The exception factory provided for the exception id"
                + f" {exception_id} within the status code {status_code}"
            )
            if exception_id and status_code
            else "The provided exception factory"
        )

    @classmethod
    def _inspect_factory_params(
        cls,
        factory: ExceptionFactory,
        *,
        exception_id: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> Sequence[ExceptionFactoryParam]:
        """Inspect the parameters of the given factory.

        Raises:
            ValidationError: if parameters are invalid.

        Returns:
            A sequence of required parameters.
        """
        try:
            factory_signature = inspect.signature(factory)
        except ValueError:
            factory_signature = inspect.signature(factory.__call__)  # type: ignore

        # check parameter order:
        observed_params = list(factory_signature.parameters.keys())
        filtered_expected_params = [
            param for param in EXCEPTION_FACTORY_PARAMS if param in observed_params
        ]
        if observed_params != filtered_expected_params:
            raise ValidationError(
                f"{cls._get_error_intro(status_code, exception_id)} had the wrong order,"
                + " expected [{','.join(filtered_expected_params)}], but obtained:"
                + f"[{','.join(observed_params)}]"
            )

        # check additional paramters:
        additional_params = [
            param for param in observed_params if param not in EXCEPTION_FACTORY_PARAMS
        ]
        for param in additional_params:
            param_value = factory_signature.parameters[param]
            if param_value.kind in {
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            }:
                raise ValidationError(
                    f"{cls._get_error_intro(status_code, exception_id)} had variadic"
                    + "argument or keyword arguments (e.g. *args or **kwargs) which are"
                    + " not allowed."
                )

            raise ValidationError(
                f"{cls._get_error_intro(status_code, exception_id)} has an"
                + " unexpected parameter (expected one or multiple of"
                + f" [{','.join(EXCEPTION_FACTORY_PARAMS)}] in that order):"
                + param
            )

        # return required parameters:
        return cast(
            list[ExceptionFactoryParam],
            [param for param in observed_params if param in EXCEPTION_FACTORY_PARAMS],
        )

    @classmethod
    def _check_exception_factory(
        cls,
        factory: object,
        *,
        exception_id: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> None:
        """Check the signature of an exception factory."""
        if not callable(factory):
            raise ValidationError(
                f"{cls._get_error_intro(status_code, exception_id)} was not callable."
            )

        cls._inspect_factory_params(
            factory, exception_id=exception_id, status_code=status_code
        )

    @classmethod
    def _validate(cls, spec: ExceptionMappingSpec):
        """Validate a dict-based specification of a exception mappings.

        Raises:
            ValidationError: if validation fails.
        """
        for status_code, exc_id_mapping in spec.items():
            assert_error_code(status_code)
            cls._check_exception_id_mapping(exc_id_mapping, status_code=status_code)
            exc_id_mapping = cast(Mapping[ExceptionId, Any], exc_id_mapping)

            for exception_id, exception_factory in exc_id_mapping.items():
                validate_exception_id(exception_id, status_code=status_code)
                cls._check_exception_factory(
                    exception_factory,
                    exception_id=exception_id,
                    status_code=status_code,
                )

    def _select_factory(
        self, *, status_code: int, exception_id: str
    ) -> ExceptionFactory:
        """Select and return an ExceptionFactory by providing mapping parameters.

        Args:
            status_code:
                Must correspond to an HTTP error code (4xx or 5xx).
            exception_id:
                An identifier used to distinguish between different exception causes.

        Raises:
            ValidationError: If not passing an HTTP error code.
        """
        assert_error_code(status_code)

        try:
            return self._spec[status_code][exception_id]
        except KeyError:
            return self._fallback_factory

    def get_factory_kit(self, *, status_code: int, exception_id: str) -> FactoryKit:
        """Obtain a FactoryKit by providing mapping parameters.

        Args:
            status_code:
                Must correspond to an HTTP error code (4xx or 5xx).
            exception_id:
                An identifier used to distinguish between different exception causes.

        Returns:
            A FactoryKit.

        Raises:
            ValidationError: If not passing an HTTP error code.
        """
        factory = self._select_factory(
            status_code=status_code, exception_id=exception_id
        )
        required_params = self._inspect_factory_params(
            factory, status_code=status_code, exception_id=exception_id
        )

        return FactoryKit(factory=factory, required_params=required_params)
