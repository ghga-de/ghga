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

"""Logic for exporting schemapacks in mermaid format."""

from collections.abc import Mapping, Sequence
from typing import Any

from schemapack._internals.spec.schemapack import ClassDefinition, ClassRelation
from schemapack.spec.schemapack import SchemaPack


def get_property_type(json_schema_props: Mapping[str, Any], prop_name: str) -> str:
    """Get the type of a property from a JSON schema properties map. If no type is
    specified, 'object' is assumed. If the property has an enum key, 'enum' is returned.

    Args:
        json_schema_props: The properties of the class.
        prop_name: The name of the property to get the type of.

    Returns:
        The type of the property.
    """
    prop = json_schema_props[prop_name]
    if isinstance(prop, Mapping):
        type = prop.get("type", "object") if not prop.get("enum") else "enum"
        if type == "array":
            element_type = prop.get("items", {}).get("type", "object")
            return f"array[{element_type}]"
        return type
    raise ValueError(
        f"Invalid JSON schema. Expected property {prop_name} to be a mapping."
    )


def export_class_entity(
    class_name: str, class_def: ClassDefinition, content_properties: bool
) -> str:
    """
    Export a class entity in mermaid format.

    Args:
        class_name: The name of the class to export.
        class_def: The definition of the class to export.
        show_properties: Whether to include the properties of the class in the diagram.

    Returns:
        A string representing the class entity in mermaid format.
    """
    if not content_properties:
        return f"{class_name} {{}}"

    json_schema_obj_props = class_def.content.get("properties", {})
    additional_properties = class_def.content.get("additionalProperties", False)
    json_schema_obj_reqs = class_def.content.get("required", [])

    if not isinstance(json_schema_obj_reqs, Sequence):
        raise ValueError("Invalid JSON schema. Expected 'required' to be a list.")

    fields = [
        f"  {get_property_type(json_schema_props=json_schema_obj_props, prop_name=field)}"
        + f" {field} "
        + ('"req"' if field in json_schema_obj_reqs else '"opt"')
        for field in json_schema_obj_props
    ]

    if additional_properties:
        fields.append('  * * ""')

    fields_str = "\n" + "\n".join(fields) + "\n" if fields else ""

    return f"{class_name} {{{fields_str}}}"


def export_class_relation(
    class_name: str, property_name: str, relation: ClassRelation
) -> str:
    """Export a relation between two classes in mermaid format.

    Args:
        class_name: The name of the class that contains the relation.
        property_name: The name of the relation.
        relation: The relation definition.

    Returns:
        A string representing the relation between the two classes in mermaid format.
    """
    origin_multiple = "}" if relation.multiple.origin else "|"
    target_multiple = "{" if relation.multiple.target else "|"
    origin_mandatory = "|" if relation.mandatory.origin else "o"
    target_mandatory = "|" if relation.mandatory.target else "o"
    return (
        f"{class_name} "
        f"{origin_multiple}{origin_mandatory}--"
        + f"{target_mandatory}{target_multiple}"
        + f' {relation.targetClass} : "{class_name}.{property_name}"'
    )


def export_class(
    class_name: str, class_def: ClassDefinition, content_properties: bool
) -> str:
    """Export a class in mermaid format.

    Args:
        class_name: The name of the class to export.
        class_def: The definition of the class to export.
        show_properties: Whether to include the properties of the class in the diagram.

    Returns:
        A string representing the class in mermaid format.
    """
    class_str = export_class_entity(
        class_name=class_name,
        class_def=class_def,
        content_properties=content_properties,
    )

    relations_str = (
        "\n\n"
        + "\n".join(
            export_class_relation(class_name, prop_name, relation)
            for prop_name, relation in class_def.relations.items()
        )
        if class_def.relations
        else ""
    )

    return class_str + relations_str


def export_mermaid(schemapack: SchemaPack, content_properties: bool = True) -> str:
    """
    Export a SchemaPack in mermaid format.

    Args:
        schemapack: The SchemaPack to export.
        show_properties: Whether to include the properties of the classes in the diagram.

    Returns:
        A string representing the SchemaPack in mermaid format.
    """
    erd_str = "erDiagram\n\n" + "\n\n".join(
        export_class(
            class_name=class_name,
            class_def=class_def,
            content_properties=content_properties,
        )
        for class_name, class_def in schemapack.classes.items()
    )

    return erd_str
