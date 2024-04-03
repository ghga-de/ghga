# Copyright 2024 Kersten Henrik Breuer
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

"""Test the Pydantic integration of the FrozenDict class."""

import json
from typing import Any

import pydantic
import pytest
from arcticfreeze import FrozenDict
from pydantic import BaseModel, ConfigDict


def test_frozen_dict_validation():
    """Test validation and type conversion using FrozenDict in pydantic models."""

    class TestModel(BaseModel):
        frozen_dict: FrozenDict

    input_dict = {"a": 1, "b": 2}
    frozen_input_dict = FrozenDict(input_dict)

    model_from_dict = TestModel.model_validate({"frozen_dict": input_dict})
    model_from_frozendict = TestModel(frozen_dict=frozen_input_dict)

    assert (
        model_from_dict.frozen_dict
        == model_from_frozendict.frozen_dict
        == frozen_input_dict
    )


def test_frozen_dict_validation_invalid():
    """Test validation using FrozenDict in pydantic models with invalid input."""

    class TestModel(BaseModel):
        frozen_dict: FrozenDict

    with pytest.raises(pydantic.ValidationError):
        TestModel.model_validate({"frozen_dict": ["invalid_input"]})


def test_frozen_dict_validation_with_args():
    """Test validation and type conversion using FrozenDict with type arguments in
    pydantic models.
    """

    class TestModel(BaseModel):
        frozen_dict: FrozenDict[str, int]

    input_dict = {"a": 1, "b": 2}
    frozen_input_dict = FrozenDict(input_dict)

    model_from_dict = TestModel.model_validate({"frozen_dict": input_dict})
    model_from_frozendict = TestModel(frozen_dict=frozen_input_dict)

    assert (
        model_from_dict.frozen_dict
        == model_from_frozendict.frozen_dict
        == frozen_input_dict
    )


def test_frozen_dict_validation_with_args_invalid():
    """Test validation and type conversion using FrozenDict with type arguments in
    pydantic models with invalid input.
    """

    class TestModel(BaseModel):
        frozen_dict: FrozenDict[str, int]

    # values are strings but expected integers:
    input_dict = {"a": "invalid", "b": "invalid"}

    with pytest.raises(pydantic.ValidationError):
        TestModel.model_validate({"frozen_dict": input_dict})


def test_frozen_dict_hashing():
    """Test hashing and comparison of pydantic models using FrozenDicts."""

    class TestModel(BaseModel):
        frozen_dict: FrozenDict

        model_config = ConfigDict(frozen=True)

    input_dict = {"a": 1, "b": 2}

    test1 = TestModel.model_validate({"frozen_dict": input_dict})
    test2 = TestModel.model_validate({"frozen_dict": input_dict})

    assert hash(test1) == hash(test2)
    assert test1 == test2


def test_frozen_dict_nesting():
    """Test nested pydantic models using FrozenDict."""

    class Inner(BaseModel):
        frozen_dict: FrozenDict

    class TestModel(BaseModel):
        inner: FrozenDict[str, Inner]

    input_dict = {"a": 1, "b": 2}

    model = TestModel.model_validate({"inner": {"test": {"frozen_dict": input_dict}}})
    assert isinstance(model.inner["test"], Inner)


def test_frozen_dict_json_schema():
    """Test JSON schema generation of FrozenDicts-containing pydantic models."""

    class TestModel(BaseModel):
        frozen_dict: FrozenDict

    schema_from_frozen_dict = TestModel.model_json_schema()

    # redefine TestModel to not using standard dict:
    class TestModel(BaseModel):  # type: ignore
        frozen_dict: dict

    schema_from_dict = TestModel.model_json_schema()

    assert schema_from_frozen_dict == schema_from_dict


def test_frozen_dict_serialization():
    """Test serialization of FrozenDict used in pydantic models when using model_dump."""

    class TestModel(BaseModel):
        frozen_dict: FrozenDict

    input_dict = {"a": 1, "b": 2}

    model = TestModel.model_validate({"frozen_dict": input_dict})

    dumped_data = model.model_dump()
    observed_dict = dumped_data["frozen_dict"]
    assert isinstance(observed_dict, FrozenDict)
    assert dict(observed_dict) == input_dict

    dumped_json = model.model_dump_json()
    observed_json_dict = json.loads(dumped_json)["frozen_dict"]
    assert observed_json_dict == input_dict


def test_frozen_dict_serialization_when_not_announced():
    """Test serialization of FrozenDict when not announced in the model. Moreover,
    check that also the serialization of children of the FrozenDict is working.
    This test was added as response to a bug.
    """

    class TestModel(BaseModel):
        """A model defining a tuple with arbitrary content (hence also FrozenDict)
        should be valid.
        """

        frozen_tuple: tuple[Any]

    input_tuple = (FrozenDict({"a": (1, 2)}),)
    model = TestModel.model_validate({"frozen_tuple": input_tuple})

    # serialization to dict:
    dumped_dict = model.model_dump()
    observed_output = dumped_dict["frozen_tuple"]
    assert observed_output == input_tuple

    # serialization to json:
    dumped_json = model.model_dump_json()
    expected_json_output = [{"a": [1, 2]}]
    observed_json_output = json.loads(dumped_json)["frozen_tuple"]
    assert observed_json_output == expected_json_output
