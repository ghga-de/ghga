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

"""Integrate rooted datapacks into nested json objects."""

from collections import defaultdict
from collections.abc import Mapping
from typing import Optional

from typing_extensions import TypeAlias

from schemapack.exceptions import CircularRelationError, ValidationAssumptionError
from schemapack.spec.datapack import ClassName, DataPack, ResourceId
from schemapack.spec.schemapack import SchemaPack

JsonObjectCompatible: TypeAlias = dict[str, object]


def integrate(  # noqa: PLR0912,C901
    *,
    datapack: DataPack,
    schemapack: SchemaPack,
    _resource_blacklist: Optional[Mapping[ClassName, set[ResourceId]]] = None,
    _alt_root_class_name: Optional[ClassName] = None,
    _alt_root_resource_id: Optional[ResourceId] = None,
) -> JsonObjectCompatible:
    """Integrate a rooted datapack into a nested json object-compatible data structure.
    It is assumed that the provided datapack has already been validated against the
    provided schemapack.

    Args:
        datapack:
            The datapack to be integrated. Must be rooted.
        schemapack:
            The schemapack to be used for looking up the classes of relations.
        _resource_blacklist:
            An optional blacklist of resources (a mapping with resource ids as values
            and class names as keys) that cause an error to be raised if they are
            encountered when assembling the json compatible object. This is only used
            internally to prevent circular relations.
        _alt_root_class_name:
            An optional alternative root class name to be used instead of the class
            name specified as root in the datapack. This is only used internally for
            recursive calls.
        _alt_root_resource_id:
            An optional alternative root resource id to be used instead of the resource
            id specified as root in the datapack. This is only used internally for
            recursive calls.

    Raises:
        ValueError:
            If the datapack is not rooted.
        schemapack.exceptions.ValidationAssumptionError:
            If the datapack is not valid against the schemapack.
        schemapack.exceptions.CircularRelationError:
            If a circular relation is detected.
    """
    if not datapack.root:
        raise ValueError("Datapack must be rooted.")

    root_class_name = _alt_root_class_name or datapack.root.class_name
    root_resource_id = _alt_root_resource_id or datapack.root.resource_id

    resource_blacklist: dict[ClassName, set[ResourceId]] = defaultdict(set)
    resource_blacklist[root_class_name].add(root_resource_id)
    if _resource_blacklist:
        for class_name, resource_ids in _resource_blacklist.items():
            resource_blacklist[class_name].update(resource_ids)

    root_resource = datapack.resources[root_class_name][root_resource_id]
    try:
        root_class_definition = schemapack.classes[root_class_name]
    except KeyError as error:
        raise ValidationAssumptionError(context="class lookup") from error

    integrated_object: JsonObjectCompatible = {
        root_class_definition.id_property: root_resource_id
    }
    integrated_object.update(root_resource.content)

    for relation_name, foreign_ids in root_resource.relations.items():
        if isinstance(foreign_ids, str):
            foreign_ids = [foreign_ids]

        try:
            relation_definition = root_class_definition.relations[relation_name]
        except KeyError as error:
            raise ValidationAssumptionError(context="relation resolution") from error

        foreign_class_name = relation_definition.to

        is_plural = relation_definition.cardinality.endswith("to_many")
        if is_plural:
            integrated_object[relation_name] = []

        for foreign_id in foreign_ids:
            if (
                foreign_class_name in resource_blacklist
                and foreign_id in resource_blacklist[foreign_class_name]
            ):
                raise CircularRelationError(
                    "Cannot perform integration of datapack with circular relations."
                    + " The circular relation involved the resource with id"
                    + f" {foreign_id} of class {foreign_class_name}."
                )

            foreign_resource = integrate(
                datapack=datapack,
                schemapack=schemapack,
                _resource_blacklist=resource_blacklist,
                _alt_root_class_name=foreign_class_name,
                _alt_root_resource_id=foreign_id,
            )

            if is_plural:
                integrated_object[relation_name].append(foreign_resource)  # type: ignore
            else:
                integrated_object[relation_name] = foreign_resource

    return integrated_object
