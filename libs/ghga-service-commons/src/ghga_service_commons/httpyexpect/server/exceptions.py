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

"""Exception Base models used across all servers."""

from abc import ABC
from typing import Literal

import pydantic
from pydantic import ConfigDict

from ghga_service_commons.httpyexpect.base_exception import HttpyExpectError
from ghga_service_commons.httpyexpect.models import HttpExceptionBody
from ghga_service_commons.httpyexpect.validation import (
    ValidationError,
    assert_error_code,
)


class HttpException(HttpyExpectError):
    """A generic exception model.

    This can be translated into an HTTP response according to the httpyexpect exception
    schema.
    """

    def __init__(
        self, *, status_code: int, exception_id: str, description: str, data: dict
    ):
        """Initialize the error with the required metadata.

        Args:
            status_code:
                The response code of the HTTP response to send.
            exception_id:
                An identifier used to distinguish between different exception causes in
                a preferably fine-grained fashion. The distinction between causes should
                be made from the perspective of the server/service raising the exception
                (and not from the client perspective). Needs to be camel case formatted
                and 3-40 character in length.
            description:
                A human readable message to the client explaining the cause of the
                exception.
            data:
                An object containing further details on the exception cause in a machine
                readable way.  All exceptions with the same exception_id should use the
                same set of properties here. This object may be empty (in case no data
                is required)"
        """
        assert_error_code(status_code)
        self.status_code = status_code

        # prepare a body that is validated against the httpyexpect schema:
        try:
            self.body = HttpExceptionBody(
                exception_id=exception_id, description=description, data=data
            )
        except pydantic.ValidationError as error:
            raise ValidationError(
                "Validation against basic HTTP exception body model failed."
            ) from error

        super().__init__(description)


class HttpCustomExceptionBase(ABC, HttpException):
    """A base class for creating HTTP exceptions with custom response body models.

    Usage:
        - subclass this abstract class
        - define the exception_id attribute
        - optionally, overwrite the DataModel sub-class
    """

    exception_id: str

    class DataModel(pydantic.BaseModel):
        """An empty model used as default for describing exception data.

        Please overwrite this to define your own data model.
        """

        model_config = ConfigDict(extra="allow")

    def __init__(self, *, status_code: int, description: str, data: dict):
        """Initialize the error with the required metadata.

        Args:
            status_code:
                The response code of the HTTP response to send.
            description:
                A human readable message to the client explaining the cause of the
                exception.
            data:
                An object containing further details on the exception cause in a machine
                readable way.  All exceptions with the same exception_id should use the
                same set of properties here. This object may be empty (in case no data
                is required)"
        """
        self._check_data_model_cls()

        # validate the data against the custom model:
        try:
            self.DataModel(**data)
        except pydantic.ValidationError as error:
            raise ValidationError(
                "Validation of data against custom model failed."
            ) from error

        super().__init__(
            status_code=status_code,
            exception_id=self.exception_id,
            description=description,
            data=data,
        )

    @classmethod
    def _check_data_model_cls(cls):
        """Make sure that the DataModel class has the right base."""
        if not issubclass(cls.DataModel, pydantic.BaseModel):
            raise TypeError("The DataModel is not a subclass of pydantic's BaseModel.")

    @classmethod
    def get_body_model(cls):
        """Create and return a custom pydantic model describing the exception body."""
        cls._check_data_model_cls()

        body_model_name = cls.__name__

        # derive the name of the exception data model:
        data_model_name = f"{body_model_name}Data"

        # customize the class name by subclassing:
        named_data_model = type(data_model_name, (cls.DataModel,), {})

        class CustomBodyModel(HttpExceptionBody):
            """A custom exception body model."""

            exception_id: Literal[cls.exception_id]  # type: ignore
            data: named_data_model  # type: ignore
            model_config = ConfigDict(extra="forbid")

        # customize the class name by subclassing:
        named_custom_model = type(body_model_name, (CustomBodyModel,), {})

        return named_custom_model
