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

"""Test the base exception for servers."""

import pydantic
import pytest

from ghga_service_commons.httpyexpect.models import HttpExceptionBody
from ghga_service_commons.httpyexpect.server import (
    HttpCustomExceptionBase,
    HttpException,
)
from ghga_service_commons.httpyexpect.validation import ValidationError


class MyCustomHttpException(HttpCustomExceptionBase):
    """An exception subclassing HttpCustomExceptionBase."""

    exception_id = "myHttpException"

    class DataModel(pydantic.BaseModel):
        """Dummy data class."""

        some_param: str
        another_param: int


def test_http_exception():
    """Tests the interface and behavior of HTTPException instances."""
    # example params for an http exception
    status_code = 400
    body = HttpExceptionBody(
        exception_id="testException",
        description="This is a test exception.",
        data={"test": "test"},
    )

    # create an exception:
    exception = HttpException(
        status_code=status_code,
        exception_id=body.exception_id,
        description=body.description,
        data=body.data,
    )

    # check public attributes:
    assert exception.body == body
    assert exception.status_code == status_code

    # check error message:
    assert str(exception) == body.description


@pytest.mark.parametrize(
    "status_code, exception_id, description, data",
    [
        # invalid status codes:
        (200, "myValidExceptionID", "A valid description", {"valid": "data"}),
        (600, "myValidExceptionID", "A valid description", {"valid": "data"}),
        # invalid exception id:
        (400, "123myInvalidExceptionID", "A valid description", {"valid": "data"}),
        (400, "myInvalidExcßeptionID", "A valid description", {"valid": "data"}),
        # invalid data:
        (400, "myValidExceptionID", "A valid description", 123),
    ],
)
def test_http_exception_invalid_params(
    status_code: object, exception_id: object, description: object, data: object
):
    """Tests creating an HTTPException with invalid params."""
    with pytest.raises(ValidationError):
        HttpException(
            status_code=status_code,  # type: ignore
            exception_id=exception_id,  # type: ignore
            description=description,  # type: ignore
            data=data,  # type: ignore
        )


def test_http_custom_exception():
    """Test HttpCustomExceptionBase.

    Tests the interface and behavior of instances of subclasses of the
    HttpCustomExceptionBase.
    """
    # example params for an http exception
    status_code = 400
    body = HttpExceptionBody(
        exception_id=MyCustomHttpException.exception_id,
        description="This is a test exception.",
        data={"some_param": "data", "another_param": 123},
    )

    # create an exception:
    exception = MyCustomHttpException(
        status_code=status_code,
        description=body.description,
        data=body.data,
    )

    # check public attributes:
    assert exception.body == body
    assert exception.status_code == status_code

    # check error message:
    assert str(exception) == body.description


def test_http_custom_exception_body():
    """Tests the interface and behavior of HttpCustomExceptionBase instances."""
    body_model = MyCustomHttpException.get_body_model()
    assert issubclass(body_model, pydantic.BaseModel)

    # evaluate the schema:
    body_schema = body_model.schema()
    assert set(body_schema["properties"].keys()) == {
        "data",
        "description",
        "exception_id",
    }

    exception_id_schema = body_schema["properties"]["exception_id"]
    assert exception_id_schema["type"] == "string"
    assert "enum" in exception_id_schema
    assert exception_id_schema["enum"][0] == MyCustomHttpException.exception_id

    assert "$ref" in body_schema["properties"]["data"]
    data_definition_name = body_schema["properties"]["data"]["$ref"].split("/")[-1]
    data_definition = body_schema["definitions"][data_definition_name]
    assert data_definition["type"] == "object"
    assert set(data_definition["properties"].keys()) == {"some_param", "another_param"}


@pytest.mark.parametrize(
    "status_code, description, data",
    [
        # invalid status codes:
        (200, "A valid description", {"some_param": "data", "another_param": 123}),
        (600, "A valid description", {"some_param": "data", "another_param": 123}),
        # invalid data:
        (400, "A valid description", {}),
        (400, "A valid description", {"some_random_param": "data"}),
    ],
)
def test_http_custom_exception_invalid_params(
    status_code: object, description: object, data: object
):
    """Tests the interface and behavior of HttpCustomExceptionBase instances."""
    with pytest.raises(ValidationError):
        MyCustomHttpException(
            status_code=status_code,  # type: ignore
            description=description,  # type: ignore
            data=data,  # type: ignore
        )
