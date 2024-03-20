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

"""Custom types annotations used for type hinting."""

from collections.abc import Mapping
from typing import Annotated as _Annotated
from typing import TypeVar

from immutabledict import immutabledict
from pydantic import AfterValidator, PlainSerializer
from pydantic import Field as _Field
from typing_extensions import TypeAlias as _TypeAlias

__all__ = [
    "ClassName",
    "ResourceId",
    "RelationPropertyName",
    "ContentPropertyName",
    "IdPropertyName",
]

_NonEmptyStr: _TypeAlias = _Annotated[str, _Field(..., min_length=1)]
ClassName: _TypeAlias = _NonEmptyStr
ResourceId: _TypeAlias = _NonEmptyStr
RelationPropertyName: _TypeAlias = _NonEmptyStr
ContentPropertyName: _TypeAlias = _NonEmptyStr
IdPropertyName: _TypeAlias = _NonEmptyStr

_K = TypeVar("_K")
_V_co = TypeVar("_V_co", covariant=True)
FrozenDict = _Annotated[
    Mapping[_K, _V_co],
    AfterValidator(lambda x: immutabledict(x)),
    PlainSerializer(lambda x: dict(x)),
]
