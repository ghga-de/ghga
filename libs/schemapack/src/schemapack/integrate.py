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
    if not datapack.root_resource:
        raise ValueError("Datapack must be rooted.")

    if not schemapack.root_class:
        raise ValueError("Schemapack must be rooted.")

    root_class_name = _alt_root_class_name or schemapack.root_class
    root_resource_id = _alt_root_resource_id or datapack.root_resource

    resource_blacklist: dict[ClassName, set[ResourceId]] = defaultdict(set)
    resource_blacklist[root_class_name].add(root_resource_id)
    if _resource_blacklist:
        for class_name, resource_ids in _resource_blacklist.items():
            resource_blacklist[class_name].update(resource_ids)

    root_class_resources = datapack.resources.get(root_class_name)
    if not root_class_resources:
        raise ValidationAssumptionError(context="root class lookup")

    root_resource = root_class_resources.get(root_resource_id)
    if not root_resource:
        raise ValidationAssumptionError(context="root resource lookup")

    root_class_definition = schemapack.classes.get(root_class_name)
    if not root_class_definition:
        raise RuntimeError(
            "This is a bug and should not happen. It should be caught by the schemapack"
            + " spec validation."
        )

    integrated_object: JsonObjectCompatible = {
        root_class_definition.id_property: root_resource_id
    }
    integrated_object.update(root_resource.content)

    for relation_name, target_ids in root_resource.relations.items():
        try:
            relation_definition = root_class_definition.relations[relation_name]
        except KeyError as error:
            raise ValidationAssumptionError(context="relation resolution") from error

        target_class_name = relation_definition.targetClass

        if isinstance(target_ids, list):
            integrated_object[relation_name] = []

            for target_id in target_ids:
                if (
                    target_class_name in resource_blacklist
                    and target_id in resource_blacklist[target_class_name]
                ):
                    raise CircularRelationError(
                        "Cannot perform integration of datapack with circular relations."
                        + " The circular relation involved the resource with id"
                        + f" {target_id} of class {target_class_name}."
                    )

                target_resource = integrate(
                    datapack=datapack,
                    schemapack=schemapack,
                    _resource_blacklist=resource_blacklist,
                    _alt_root_class_name=target_class_name,
                    _alt_root_resource_id=target_id,
                )

                integrated_object[relation_name].append(target_resource)  # type: ignore

        elif isinstance(target_ids, str):
            integrated_object[relation_name] = integrate(
                datapack=datapack,
                schemapack=schemapack,
                _resource_blacklist=resource_blacklist,
                _alt_root_class_name=target_class_name,
                _alt_root_resource_id=target_ids,
            )

        else:
            integrated_object[relation_name] = None

    return integrated_object
