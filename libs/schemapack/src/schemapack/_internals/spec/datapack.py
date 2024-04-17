# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Models representing the datapack spec.

Warning: This is an internal part of the library and might change without notice.
"""

import typing
from collections import Counter
from collections.abc import Iterable
from typing import Annotated, Any, Literal, Optional, Union

import arcticfreeze
from arcticfreeze import FrozenDict
from pydantic import BeforeValidator, Field, WrapSerializer
from pydantic_core import PydanticCustomError
from typing_extensions import TypeAlias

from schemapack._internals.spec.base import _FrozenNoExtraBaseModel
from schemapack._internals.spec.custom_types import (
    ClassName,
    RelationPropertyName,
    ResourceId,
)

SupportedDataPackVersions = Literal["0.3.0"]
SUPPORTED_DATA_PACK_VERSIONS = typing.get_args(SupportedDataPackVersions)


def validate_duplicate_target_ids(iterable: Iterable) -> Any:
    """Checks that the given iterable of target IDs does not contain duplicates. If it
    does, a PydanticCustomError with name "DuplicateTargetIdError" is raised. Otherwise,
    the given iterable is returned.
    """
    if isinstance(iterable, frozenset):
        return iterable

    try:
        target_id_list = list(iterable)
    except TypeError as error:
        raise PydanticCustomError(
            "TargetIdsParsingError",
            "The provided object is not iterable.",
            {"iterable": iterable},
        ) from error

    counter = Counter(target_id_list)
    duplicates = {k for k, v in counter.items() if v > 1}

    if duplicates:
        raise PydanticCustomError(
            "DuplicateTargetIdError",
            "The given sequence of target ids contain duplicates: {duplicates}",
            {"duplicates": duplicates},
        )

    return iterable


ResourceIdSet: TypeAlias = Annotated[
    frozenset[str],
    # Upon serialization, assert that the provided sequence does not contain duplicates:
    BeforeValidator(validate_duplicate_target_ids),
    # Upon serialization, produce predictablily sorted lists:
    WrapSerializer(lambda v, next_: sorted(next_(v))),
]

ContentPropertyValue: TypeAlias = Annotated[
    Any,
    # the value of a content property is deeply frozen:
    BeforeValidator(arcticfreeze.freeze),
]


class Resource(_FrozenNoExtraBaseModel):
    """A model defining content and relations of a resource
    of a specific class.
    """

    content: FrozenDict[str, ContentPropertyValue] = Field(
        ...,
        description=(
            "The content of the resource that complies with the content schema defined"
            + " in the corresponding schemapack."
        ),
    )

    relations: FrozenDict[
        RelationPropertyName, Union[Optional[ResourceId], ResourceIdSet]
    ] = Field(
        FrozenDict(),
        description=(
            "A dictionary containing the relations of the resource to other resources."
            + " Each key correspond to the name of a relation property as per the"
            + " schemapack definition. Each value could be one of the following types"
            + " depending on the corresponding schemapack definition:"
            + " (1) a id of a single target resource (multiple.target is False),"
            + " (2) None (multiple.target and mandatory.target are both False),"
            + " (3) a set of ids of target resources (multiple.target is True),"
            + " (4) an empty set (multiple.target is True and mandatory.target is"
            + " False)."
        ),
    )

    def get_target_id_set(
        self, relation_name: RelationPropertyName, do_not_raise: bool = False
    ) -> frozenset[ResourceId]:
        """Get the target ids for the given relation always represented as a set.
        This is even the case if the actual value in the relations dict is a single
        string (translated into a list of length one) or None (translated into an
        empty set). If do_not_raise is True, the method will return an empty set
        even if the relation name does not exist in the relations dict.

        Raises:
            KeyError:
                If the given relation name does not exist in the relations dict and
                do_not_raise is False.
        """
        try:
            targets = self.relations[relation_name]
        except KeyError:
            if do_not_raise:
                return frozenset()
            raise

        if targets is None:
            return frozenset()
        if isinstance(targets, frozenset):
            return targets
        return frozenset({targets})


class DataPack(_FrozenNoExtraBaseModel):
    """A model for describing a schemapack definition."""

    datapack: SupportedDataPackVersions = Field(
        ...,
        description=(
            "Has two purposes: (1) it clearly identifies a YAML/JSON document as"
            + " a datapack definition and (2) it specifies the used version of the"
            + " datapack specification."
        ),
    )

    resources: FrozenDict[ClassName, FrozenDict[ResourceId, Resource]] = Field(
        ...,
        description=(
            "A nested dictionary containing resources per class name (keys on the first"
            + " level) and resource ID (keys on the second level). Each class defined"
            + " in the schemapack must be present even if no resources are defined for"
            + " it in this datapack."
        ),
    )

    rootResource: Optional[str] = Field(  # noqa: N815 - following JSON conventions
        None,
        description=(
            "Defines the id of the resource that should act as root. This means"
            + " that, in addition to the root resource itself, the datapack must only"
            + " contain resources that are direct or indirect (dependencies of"
            + " dependencies) of the root resource."
            + " Please note, the datapack must define a root resource if the"
            + " corresponding schemapack defines a root class and vice versa."
        ),
    )
