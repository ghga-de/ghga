# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
from collections.abc import Iterable, Mapping
from typing import Annotated, Any, Literal, Self, TypeAlias

from arcticfreeze import FrozenDict, freeze
from pydantic import BeforeValidator, Field, WrapSerializer, model_validator
from pydantic_core import PydanticCustomError

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
    BeforeValidator(lambda obj: freeze(obj, by_superclass=True)),
]


class ResourceRelation(_FrozenNoExtraBaseModel):
    """A model defining relations of a resource to other resources."""

    targetClass: ClassName = Field(  # noqa: N815 - following JSON conventions
        ...,
        description=("The name of the target class of the relation."),
    )
    targetResources: ResourceId | ResourceIdSet | None = Field(  # noqa: N815 - following JSON conventions
        ...,
        description=(
            "Provides the ID(s) of target resources of the targetClass. Depending on"
            + " the corresponding schemapack definition, this field could be one of the"
            + " following types:"
            + " (1) a id of a single target resource (schemapack assumes that"
            + " multiple.target is False),"
            + " (2) None (schemapack assumes that multiple.target and mandatory.target"
            + " are both False),"
            + " (3) a set of ids of target resources (schemapack assumes that"
            + " multiple.target is True),"
            + " (4) an empty set (schemapack assumes that multiple.target is True and"
            + " mandatory.target is False)."
        ),
    )

    def get_target_resources_as_set(self) -> frozenset[ResourceId]:
        """Get target resources as a set independent of the multiplicity or
        mandatoriness. This is even the case if the actual value in the relations dict
        is a single
        string (translated into a list of length one) or None (translated into an
        empty set). If do_not_raise is True, the method will return an empty set
        even if the relation name does not exist in the relations dict.
        """
        if self.targetResources is None:
            return frozenset()
        if isinstance(self.targetResources, frozenset):
            return self.targetResources
        return frozenset({self.targetResources})


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

    relations: FrozenDict[RelationPropertyName, ResourceRelation] = Field(
        FrozenDict(),
        description=(
            "A dictionary containing the relations of the resource to other resources."
            + " Each key correspond to the name of a relation property. Each value"
            + "  contains the target class and target resource(s) of the relation."
        ),
    )


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

    rootResource: str | None = Field(  # noqa: N815 - following JSON conventions
        None,
        description=(
            "Defines the id of the resource of the class defined in `className`"
            + " that should act as root. This means"
            + " that, in addition to the root resource itself, the datapack must only"
            + " contain resources that are direct or indirect (dependencies of"
            + " dependencies) of the root resource."
        ),
    )

    rootClass: ClassName | None = Field(  # noqa: N815 - following JSON conventions
        None,
        description=(
            "Defines the class name of the resource that should act as root. This means"
            + " that, in addition to the root resource itself, the datapack must only"
            + " contain resources that are direct or indirect (dependencies of"
            + " dependencies) of the root resource."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def check_root_duality(cls, value: Mapping) -> Mapping | None:
        """Ensures that both 'rootClass' and 'rootResource' are either present or absent."""
        missing = [key for key in ("rootClass", "rootResource") if not value.get(key)]

        if len(missing) == 1:
            raise PydanticCustomError(
                "DatapackRootDualityError",
                "Invalid DataPack due to missing field '{missing}'.",
                {"missing": missing[0]},
            )

        return value

    @model_validator(mode="after")
    def validate_root_class(self) -> Self:
        """Checks if 'rootClass' exists in DataPack resources when specified."""
        if self.rootClass and self.rootClass not in self.resources:
            raise PydanticCustomError(
                "UnknownRootClassError",
                "The class '{root_class}'"
                + " given as root class does not exist among the DataPack resources",
                {"root_class": self.rootClass},
            )
        return self

    @model_validator(mode="after")
    def validate_root_resource(self) -> Self:
        """Checks if 'rootResource' exists in DataPack resources when specified."""
        if self.rootClass and self.rootResource not in self.resources[self.rootClass]:
            raise PydanticCustomError(
                "UnkownRootResourceError",
                "The specified root resource with ID '{root_resource}' of class "
                + " '{root_class}' does not exist.",
                {"root_resource": self.rootResource, "root_class": self.rootClass},
            )
        return self

    @model_validator(mode="after")
    def validate_relation_classes(self) -> Self:
        """Checks if the `targetClass` of relations defined in a datapack exists
        within datapack resources.
        """
        non_found_classes: dict[str, str] = {}  # target_class -> relation_name

        for resources in self.resources.values():
            for resource in resources.values():
                for relation_name, relation in resource.relations.items():
                    if relation.targetClass not in self.resources:
                        non_found_classes[relation.targetClass] = relation_name

        if non_found_classes:
            raise PydanticCustomError(
                "TargetClassNotFoundError",
                "Did not find the target class of the following relations (relation"
                + " names): {non_found_classes}",
                {
                    "non_found_classes": ", ".join(
                        f"'{target_class}' ('{relation_name}')"
                        for target_class, relation_name in non_found_classes.items()
                    )
                },
            )
        return self

    @model_validator(mode="after")
    def validate_relation_resources(self) -> Self:
        """Checks if the `targetResources` of relations defined in a datapack exists
        within its corresponding `targetClass`.
        """
        non_found_target_ids: dict[str, str] = {}  # target_id -> relation_name

        for resources in self.resources.values():
            for resource in resources.values():
                for relation_name, relation in resource.relations.items():
                    target_ids = relation.get_target_resources_as_set()
                    for target_id in target_ids:
                        if target_id not in self.resources.get(
                            relation.targetClass, set()
                        ):
                            non_found_target_ids[target_id] = relation_name

        if non_found_target_ids:
            raise PydanticCustomError(
                "TargetIdNotFoundError",
                "Did not find a target resource for the following ID(s) (relation"
                + " names): {non_found_target_ids}",
                {
                    "non_found_target_ids": ", ".join(
                        f"'{target_id}' ('{relation_name}')"
                        for target_id, relation_name in non_found_target_ids.items()
                    )
                },
            )
        return self
