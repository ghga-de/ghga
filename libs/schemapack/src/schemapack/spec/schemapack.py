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

"""Models for describing and working with schemapack definitions."""

import json
import typing
from functools import cached_property
from pathlib import Path
from typing import Any, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from schemapack.utils import (
    FrozenDict,
    JsonSchemaError,
    ParsingError,
    assert_valid_json_schema,
    read_json_or_yaml_mapping,
)

SupportedSchemaPackVersions = Literal["0.2.0"]
SUPPORTED_SCHEMA_PACK_VERSIONS = typing.get_args(SupportedSchemaPackVersions)


class FrozenBaseModel(BaseModel):
    """A BaseModel that cannot be changed after initialization."""

    model_config = ConfigDict(frozen=True, use_enum_values=True, extra="forbid")


class ContentSchema(FrozenBaseModel):
    """A model for describing a schemapack content schema."""

    json_schema: str = Field(
        ...,
        description=(
            "String representation of JSON schema (as a JSON-formatted string)"
            + " describing the content of the class instances."
        ),
    )

    # cannot be cached because pydantic includes cached properties in the hash and this
    # is unhashable:
    @property
    def json_schema_dict(self) -> dict[str, Any]:
        """A dict representation of the JSON schema."""
        return json.loads(self.json_schema)

    @cached_property
    def properties(self) -> frozenset[str]:
        """Returns a set of the content properties. If the content schema is not a
        JSON Schema Object (but e.g. a list), an empty set is returned.
        """
        return frozenset(self.json_schema_dict.get("properties", {}))

    @model_validator(mode="after")
    def validate_schema(self) -> "ContentSchema":
        """Make sure that the schema is a valid JSON Schema."""
        try:
            assert_valid_json_schema(self.json_schema)
        except JsonSchemaError as error:
            raise PydanticCustomError(
                "InvalidContentSchemaError",
                "The content schema is not a valid JSON schema: {error_message}",
                {"error_message": str(error)},
            ) from error

        if self.json_schema_dict.get("type") != "object":
            raise PydanticCustomError(
                "InvalidContentSchemaError",
                "The content schema must be an object.",
            )

        return self


class MandatoryRelationSpec(FrozenBaseModel):
    """A model for describing the modality of a relation. It describes the minimum
    number of instances the origin and the target end must contribute to the relation.
    """

    origin: bool = Field(
        ...,
        description=(
            "If true, the origin must participate in the relation."
            + " I.e. every instance of the target class must be connected to at least"
            + " one instance of the origin class trough this relation."
            + " If false, the participation of the origin is optional."
            + " I.e. an instance of the target class may be connected to zero or more"
            + " instances of the origin class trough this relation."
        ),
    )
    target: bool = Field(
        ...,
        description=(
            "If true, the target must participate in the relation."
            + " I.e. every instance of the origin class must be connected to at least"
            + " one instance of the target class trough this relation."
            + " If false, the participation of the target is optional."
            + " I.e. an instance of the origin class may be connected to zero or more"
            + " instances of the target class trough this relation."
        ),
    )


class MultipleRelationSpec(FrozenBaseModel):
    """A model for describing the cardinality of a relation. It describes the maximum
    number of instances the origin and the target end may contribute to the relation.

    For instance, if the origin is `True` and target is `False`, the origin may
    contribute multiple instances to the relation, while the target may at most
    contribute a single instance to the relation. This is equivalent to a 'many-to-one'
    """

    origin: bool = Field(
        ...,
        description=(
            "If true, the origin may contribute multiple instances to the relation."
            + " This is equivalent to a 'many-to-*' cardinality."
            + " If false, the origin may at most contribute a single instance to the"
            + " relation. This is equivalent to a 'one-to-*' cardinality."
        ),
    )
    target: bool = Field(
        ...,
        description=(
            "If true, the target may contribute multiple instances to the relation."
            + " This is equivalent to a '*-to-many' cardinality."
            + " If false, the target may at most contribute a single instance to the"
            + " relation. This is equivalent to a '*-to-one' cardinality."
        ),
    )


class Relation(FrozenBaseModel):
    """A model for describing a schemapack relation definition."""

    description: Optional[str] = Field(
        None,
        description="A description of the relation.",
    )
    targetClass: str = Field(  # noqa: N815 - align with the schemapack naming scheme
        ...,
        description="The name of the target class.",
    )
    mandatory: MandatoryRelationSpec = Field(
        ...,
        description=(
            "The modality of the relation. It describes the minimum number of instances"
            + " the origin and the target end must contribute to the relation."
        ),
    )
    multiple: MultipleRelationSpec = Field(
        ...,
        description=(
            "The cardinality of the relation. It describes the maximum number of"
            + " instances the origin and the target end may contribute to the relation."
            + " For instance, if the origin is `True` and target is `False`, the origin"
            + " may contribute multiple instances to the relation, while the target may"
            + " at most contribute a single instance to the relation."
            + " This is equivalent to a 'many-to-one' cardinality."
        ),
    )


class IDSpec(FrozenBaseModel):
    """A model for describing the ID property of a class definition."""

    propertyName: str = Field(  # noqa: N815 - align with the schemapack naming scheme
        ...,
        description=(
            "The name of the ID property. It must not collide with content or relations"
            + " properties."
            + "This name e.g. relavant for specifying the ID property in a"
            + " denormalized representation."
        ),
    )
    description: Optional[str] = Field(
        None,
        description="A description of the ID property.",
    )


class ClassDefinition(FrozenBaseModel):
    """A model for describing a schemapack class definition."""

    description: Optional[str] = Field(
        None,
        description=("A description of the class definition."),
    )
    id: IDSpec = Field(
        ...,
        description="The ID property of the class definition.",
    )
    content: ContentSchema
    relations: FrozenDict[str, Relation] = Field(
        FrozenDict(),
        description=(
            "A mapping of relation names to relation definitions. Relation names"
            + " should use snake_case and may only contain alphanumeric characters and"
            + " underscores. They must start with a letter."
        ),
    )

    @field_validator("content", mode="before")
    @classmethod
    def content_schema_validator(
        cls, v: Union[ContentSchema, Path, str, dict[str, Any]]
    ) -> ContentSchema:
        """Validate and convert the type of the content schema.

        If a str is provided, it must be a path to the JSON schema file and not the
        JSON-formatted string representation of the JSON schema itself.
        """
        if isinstance(v, ContentSchema):
            return v

        if isinstance(v, str):
            # assume that the string is a path to a JSON or YAML file
            v = Path(v)

        if isinstance(v, Path):
            if not v.is_file():
                absolute_path = v.absolute().resolve()
                raise PydanticCustomError(
                    "ContentSchemaNotFoundError",
                    (
                        "Content schema path does not exist or is not a file."
                        + " Absolute path: {absolute_path}"
                    ),
                    {
                        "absolute_path": absolute_path,
                    },
                )

            try:
                json_schema_dict = read_json_or_yaml_mapping(v)
            except ParsingError as error:
                raise PydanticCustomError(
                    "InvalidContentSchemaError",
                    (
                        "Content schema at the specified path could not be parsed as"
                        + " valid JSON or YAML."
                    ),
                ) from error

            return ContentSchema(json_schema=json.dumps(json_schema_dict))

        if isinstance(v, dict):
            return ContentSchema(json_schema=json.dumps(v))

        raise PydanticCustomError(
            "InvalidContentSchemaError",
            (
                "Expected an instance of class ContentSchema, a dict[str, Any], or a"
                + " path (pathlib.Path or str) to a JSON or"
                + " YAML file."
            ),
        )

    @field_serializer("content")
    def content_schema_serializer(
        self, content: ContentSchema, _info
    ) -> dict[str, Any]:
        """Serialize the content schema by representing it either as the path to the
        JSON schema (if the path is known) or as the JSON schema itself.
        """
        return self.content.json_schema_dict

    @field_validator("relations", mode="after")
    @classmethod
    def relation_name_validator(
        cls, v: FrozenDict[str, Relation]
    ) -> FrozenDict[str, Relation]:
        """Validate relation names."""
        invalid_relation_names = [
            relation_name for relation_name in v if not relation_name.isidentifier()
        ]

        if invalid_relation_names:
            raise PydanticCustomError(
                "InvalidRelationNameError",
                (
                    "Relation names may only contain alphanumeric characters and"
                    + " underscores. They must not start with a number."
                    + " Got {number} invalid names: {invalid_relation_names}"
                ),
                {
                    "number": len(invalid_relation_names),
                    "invalid_relation_names": invalid_relation_names,
                },
            )

        return v

    @model_validator(mode="after")
    def relation_content_property_collisions(self) -> "ClassDefinition":
        """Check for collisions between relations and content properties."""
        collisions = self.content.properties.intersection(set(self.relations))

        if collisions:
            raise PydanticCustomError(
                "RelationsContentPropertyCollisionError",
                (
                    "The following properties occur both in the content and the"
                    + " relations: {collisions}"
                ),
                {
                    "number": len(collisions),
                    "collisions": collisions,
                },
            )

        return self

    @model_validator(mode="after")
    def id_content_property_collisions(self) -> "ClassDefinition":
        """Check for collisions between the id property and content properties."""
        if self.id.propertyName in self.content.properties:
            raise PydanticCustomError(
                "IdContentPropertyCollisionError",
                ("The id property '{id_property}' also occurs in the content."),
                {
                    "id_property": self.id.propertyName,
                },
            )

        return self

    @model_validator(mode="after")
    def id_relations_property_collisions(self) -> "ClassDefinition":
        """Check for collisions between the id property and relations properties."""
        if self.id.propertyName in self.relations:
            raise PydanticCustomError(
                "IdRelationsPropertyCollisionError",
                ("The id property '{id_property}' also occurs in the relations."),
                {
                    "id_property": self.id.propertyName,
                },
            )

        return self


class SchemaPack(FrozenBaseModel):
    """A model for describing a schemapack definition."""

    schemapack: SupportedSchemaPackVersions = Field(
        ...,
        description=(
            "Has two purposes: (1) it clearly identifies a YAML/JSON document as"
            + " a schemapack definition and (2) it specifies the used version of the"
            + " schemapack specification."
        ),
    )
    description: Optional[str] = Field(
        None,
        description=("A description of the schemapack definition."),
    )
    classes: FrozenDict[str, ClassDefinition] = Field(
        ...,
        description=(
            "A mapping of class names to class definitions. Class names should use"
            + " PascalCase."
        ),
        min_length=1,
    )

    root_class: Optional[str] = Field(
        None,
        description=(
            "Optionally, define the name of a class that should acting as the root of"
            + " the schemapack."
            + " Corresponding datapacks must define a root resource of this class."
            + "If not specified , i.e. set to None (the default), the datapack must no"
            + " specify a root resource."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def check_schemapack_field_exists(cls, data: Any) -> Any:
        """Checks that the schemapack field exists and points to a supported version
        before doing anything else. Please note, this validation only takes place if the
        data is passed as dict. However, the data can be pretty much anything.
        """
        if isinstance(data, dict):
            if "schemapack" not in data:
                raise PydanticCustomError(
                    "MissingSchemaPackVersionError",
                    (
                        "Missing a `schemapack` field. Are you sure you have passed a"
                        + " schemapack definition?"
                    ),
                )

            if data["schemapack"] not in SUPPORTED_SCHEMA_PACK_VERSIONS:
                raise PydanticCustomError(
                    "UnsupportedSchemaPackVersionError",
                    (
                        "Unsupported schemapack version '{current_version}'."
                        " Supported versions are: {supported_versions}"
                    ),
                    {
                        "current_version": data["schemapack"],
                        "supported_versions": SUPPORTED_SCHEMA_PACK_VERSIONS,
                    },
                )

        return data

    @field_validator("classes", mode="after")
    @classmethod
    def class_name_validator(
        cls, v: FrozenDict[str, ClassDefinition]
    ) -> FrozenDict[str, ClassDefinition]:
        """Validates class names."""
        invalid_class_names = [
            class_name for class_name in v if not class_name.isidentifier()
        ]

        if invalid_class_names:
            raise PydanticCustomError(
                "InvalidClassNameError",
                (
                    "Class names may only contain alphanumeric characters and"
                    + " underscores. They must not start with a number."
                    + " Got {number} invalid names: {invalid_class_names}"
                ),
                {
                    "number": len(invalid_class_names),
                    "invalid_class_names": invalid_class_names,
                },
            )

        return v

    @model_validator(mode="after")
    def relation_to_class_validation(self) -> "SchemaPack":
        """Validate that all relations point to existing classes."""
        # store invalid relations as a set of strings ({class_name}.{relation_name}):
        invalid_relations: set[str] = set()

        for class_name, class_definition in self.classes.items():
            for relation_name, relation in class_definition.relations.items():
                if relation.targetClass not in self.classes:
                    invalid_relations.add(f"{class_name}.{relation_name}")

        if invalid_relations:
            raise PydanticCustomError(
                "RelationClassNotFoundError",
                (
                    "Found {number} relation(s) that point to non-existing classes:"
                    + " {invalid_relations}"
                ),
                {
                    "number": len(invalid_relations),
                    "invalid_relations": invalid_relations,
                },
            )

        return self

    @model_validator(mode="after")
    def root_in_classes(self) -> "SchemaPack":
        """Check that the specified root exists in the defined classes."""
        if self.root_class and self.root_class not in self.classes:
            raise PydanticCustomError(
                "RootClassNotFoundError",
                ("The specified root class '{self.root_class}' does not exist."),
                {
                    "root_class": self.root_class,
                },
            )

        return self
