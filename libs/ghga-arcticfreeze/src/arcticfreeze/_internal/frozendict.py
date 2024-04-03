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

"""An implementation of a frozen dictionary. It provides support for Pydantic v2 models
without requiring Pydantic as a dependency.
"""

from __future__ import annotations

import typing
from collections.abc import Mapping
from typing import Any, TypeVar, overload

from immutabledict import immutabledict

from arcticfreeze._internal.utils import PYDANTIC_V2_INSTALLED

_K = TypeVar("_K")
_V_co = TypeVar("_V_co", covariant=True)


class FrozenDict(immutabledict[_K, _V_co]):
    """A Mapping type that does not provide any additional methods for modification of
    its content after construction.

    It has first class support for type hints. Moreover, it is ready to be used in
    Pydantic v2 models, yet, does not require Pydantic as a dependency.

    Examples:
    ```python
    from arcticfreeze import FrozenDict

    # Construct a FrozenDict from another mapping (such as a dictionary):
    example_from_dict = FrozenDict({"a": 1, "b": 2})

    # Construct a FrozenDict from keyword arguments:
    example_from_kwargs = FrozenDict(a=1, b=2)

    # Demonstrate that both constructions are equal:
    assert example_from_dict == example_from_kwargs
    ```
    """

    @overload
    def __new__(cls, arg: Mapping[_K, _V_co]) -> FrozenDict[_K, _V_co]: ...

    @overload
    def __new__(cls, **kwargs: _V_co) -> FrozenDict[str, _V_co]: ...

    def __new__(cls, *args: Any, **kwargs: Any) -> FrozenDict:
        return super().__new__(cls, *args, **kwargs)  # type: ignore


if PYDANTIC_V2_INSTALLED:
    from pydantic import GetCoreSchemaHandler
    from pydantic_core import SchemaSerializer, core_schema

    def get_pydantic_core_schema(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Get the pydantic core schema for this type."""
        args = typing.get_args(source)
        if not args:
            key_type = Any
            value_type = Any
        elif len(args) == 2:
            key_type, value_type = args
        else:
            raise TypeError(
                "Expected exactly two (or no) type arguments for FrozenDict, got"
                + f" {len(args)}"
            )

        validation_schema = handler.generate_schema(
            Mapping[key_type, value_type]  # type: ignore
        )

        python_serialization_schema = core_schema.plain_serializer_function_ser_schema(
            lambda x: x, return_schema=core_schema.any_schema()
        )
        python_schema = core_schema.no_info_after_validator_function(
            function=cls,
            schema=validation_schema,
            serialization=python_serialization_schema,
        )

        json_serialization_schema = core_schema.plain_serializer_function_ser_schema(
            dict, return_schema=validation_schema, when_used="json"
        )
        json_schema = core_schema.no_info_after_validator_function(
            function=cls,
            schema=validation_schema,
            serialization=json_serialization_schema,
        )

        schema = core_schema.json_or_python_schema(
            json_schema=json_schema,
            python_schema=python_schema,
        )

        return schema

    def pydantic_serializer(self) -> SchemaSerializer:
        """This is needed due to issue:
        https://github.com/pydantic/pydantic/issues/7779
        """
        validation_schema = core_schema.any_schema()

        python_serialization_schema = core_schema.plain_serializer_function_ser_schema(
            lambda x: x, return_schema=validation_schema
        )
        python_schema = core_schema.any_schema(
            serialization=python_serialization_schema,
        )

        json_serialization_schema = core_schema.plain_serializer_function_ser_schema(
            dict, return_schema=validation_schema, when_used="json"
        )
        json_schema = core_schema.any_schema(
            serialization=json_serialization_schema,
        )

        schema = core_schema.json_or_python_schema(
            json_schema=json_schema,
            python_schema=python_schema,
        )

        return SchemaSerializer(schema)

    FrozenDict.__get_pydantic_core_schema__ = classmethod(  # type: ignore
        get_pydantic_core_schema
    )
    FrozenDict.__pydantic_serializer__ = property(  # type: ignore
        pydantic_serializer
    )
