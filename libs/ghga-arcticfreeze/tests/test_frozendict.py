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

"""Test the FrozenDict class."""

import json

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


def test_frozen_dict_serialization_json():
    """Test serialization of FrozenDict used in pydantic models when using
    model_dump_json.
    """

    class TestModel(BaseModel):
        frozen_dict: FrozenDict

    input_dict = {"a": 1, "b": 2}

    model = TestModel.model_validate({"frozen_dict": input_dict})

    dumped_json = model.model_dump_json()
    observed_dict = json.loads(dumped_json)["frozen_dict"]
    assert observed_dict == input_dict


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
