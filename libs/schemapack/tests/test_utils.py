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

"""Tests the utils module."""

from pydantic import BaseModel, ConfigDict

from schemapack.utils import FrozenDict


def test_frozen_dict():
    """Test initialization and exporting of/from FrozenDict instances."""

    class Test(BaseModel):
        dict_: FrozenDict

    test_dict = {1: 2}

    test_from_dict = Test.model_validate({"dict_": test_dict})
    test_from_frozendict = Test(dict_=FrozenDict(test_dict))

    assert test_from_dict.dict_ == test_from_frozendict.dict_ == FrozenDict(test_dict)

    test_dumped = test_from_dict.model_dump()
    assert test_dumped["dict_"] == test_dict


def test_frozen_dict_schema():
    """Test JSON schema validation of FrozenDicts"""

    class Test(BaseModel):
        dict_: FrozenDict

    schema_from_frozendict = Test.model_json_schema()

    # redefine Test to not using standard dict:
    class Test(BaseModel):  # type: ignore
        dict_: dict

    schema_from_dict = Test.model_json_schema()

    assert schema_from_frozendict == schema_from_dict


def test_frozen_dict_hashing():
    """Test hashing and comparison of pydantic models using FrozenDicts."""

    class Test(BaseModel):
        dict_: FrozenDict

        model_config = ConfigDict(frozen=True)

    test_dict = {1: 2}

    test1 = Test.model_validate({"dict_": test_dict})
    test2 = Test.model_validate({"dict_": test_dict})

    # make sure hash does not throw an exception
    hash(test1)

    assert test1 == test2


def test_frozen_dict_nesting():
    """Test hashing and comparison of pydantic models using FrozenDicts."""

    class Inner(BaseModel):
        dict_: FrozenDict

    class Test(BaseModel):
        inner: FrozenDict[str, Inner]

    test_dict = {1: 2}

    test1 = Test.model_validate({"inner": {"test": {"dict_": test_dict}}})
    assert isinstance(test1.inner["test"], Inner)

    test2 = Test(
        inner=FrozenDict({"test": FrozenDict({"dict_": FrozenDict(test_dict)})})
    )
    assert test1 == test2
