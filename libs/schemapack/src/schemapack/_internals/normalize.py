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

"""Integrate rooted datapacks into nested json objects."""

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, TypeAlias

from schemapack._internals.exceptions import InvalidEmbeddingProfileError
from schemapack._internals.spec.custom_types import EmbeddingProfile
from schemapack._internals.spec.datapack import Resource
from schemapack._internals.spec.schemapack import ClassDefinition
from schemapack._internals.utils import thaw
from schemapack.exceptions import CircularRelationError, ValidationAssumptionError
from schemapack.spec.custom_types import ClassName, ResourceId
from schemapack.spec.datapack import DataPack
from schemapack.spec.schemapack import SchemaPack

JsonObjectCompatible: TypeAlias = dict[str, object]


@dataclass
class DenormalizationContext:
    """Context for denormalization to group repeated arguments."""

    datapack: DataPack
    schemapack: SchemaPack
    embedding_profile: Mapping[str, Any] | None
    resource_blacklist: dict[ClassName, set[ResourceId]]


def denormalize(
    *,
    datapack: DataPack,
    schemapack: SchemaPack,
    embedding_profile: EmbeddingProfile = None,
    _resource_blacklist: Mapping[ClassName, set[ResourceId]] | None = None,
    _alt_root_class_name: ClassName | None = None,
    _alt_root_resource_id: ResourceId | None = None,
) -> JsonObjectCompatible:
    """Integrate a rooted datapack into a nested json object-compatible data structure.
    It is assumed that the provided datapack has already been validated against the
    provided schemapack.

    Args:
        datapack:
            The datapack to be denormalized. Must be rooted.
        schemapack:
            The schemapack to be used for looking up the classes of relations.
        embedding_profile:
            An optional profile defining which relations should be embedded and which
            should not. If None, all relations will be embedded. If a relation is not
            present in the profile, it will be embedded by default.
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
    if not datapack.rootResource:
        raise ValueError("Datapack must be rooted.")

    if not datapack.rootClass:
        raise ValueError("Datapack must have a root class.")

    root_class_name = _alt_root_class_name or datapack.rootClass
    root_resource_id = _alt_root_resource_id or datapack.rootResource

    resource_blacklist = _initialize_blacklist(
        embedding_profile, root_class_name, root_resource_id, _resource_blacklist
    )

    root_resource = _get_root_resource(datapack, root_class_name, root_resource_id)

    root_class_definition = _get_class_definition(schemapack, root_class_name)

    denormalized_object: JsonObjectCompatible = {
        root_class_definition.id.propertyName: root_resource_id,
        **thaw(root_resource.content),
    }

    for relation_name, resource_relations in root_resource.relations.items():
        target_ids = resource_relations.targetResources
        target_class_name = resource_relations.targetClass

        # decide whether to embed the relation 'relation_name'
        should_embed = _should_embed(embedding_profile, relation_name)

        if should_embed is False:
            denormalized_object[relation_name] = (
                [*sorted(target_ids)]
                if isinstance(target_ids, frozenset)
                else target_ids
                if isinstance(target_ids, str)
                else []
            )
            continue

        next_embedding_profile = _get_next_embedding_profile(
            embedding_profile, relation_name
        )
        denormalization_context = DenormalizationContext(
            datapack=datapack,
            schemapack=schemapack,
            embedding_profile=next_embedding_profile,
            resource_blacklist=resource_blacklist,
        )
        denormalized_object[relation_name] = _process_recursion(
            denormalization_context,
            target_class_name,
            target_ids,
        )

    return denormalized_object


def _initialize_blacklist(
    embedding_profile: EmbeddingProfile,
    root_class_name: ClassName,
    root_resource_id: ResourceId,
    _resource_blacklist: Mapping[ClassName, set[ResourceId]] | None,
) -> dict[ClassName, set[ResourceId]]:
    """Function to initialize the resource blacklist."""
    resource_blacklist: dict[ClassName, set[ResourceId]] = defaultdict(set)
    if not embedding_profile:
        resource_blacklist[root_class_name].add(root_resource_id)

    if _resource_blacklist:
        for class_name, resource_ids in _resource_blacklist.items():
            resource_blacklist[class_name].update(resource_ids)
    return resource_blacklist


def _get_root_resource(
    datapack: DataPack, root_class_name: ClassName, root_resource_id: ResourceId
) -> Resource:
    """Function to get the root resource from the datapack."""
    root_class_resources = datapack.resources.get(root_class_name)
    if not root_class_resources:
        raise ValidationAssumptionError(context="root class lookup")

    root_resource = root_class_resources.get(root_resource_id)
    if not root_resource:
        raise ValidationAssumptionError(context="root resource lookup")

    return root_resource


def _get_class_definition(
    schemapack: SchemaPack, root_class_name: ClassName
) -> ClassDefinition:
    """Function to get the class definition from the schemapack."""
    root_class_definition = schemapack.classes.get(root_class_name)
    if not root_class_definition:
        raise RuntimeError(
            "This is a bug and should not happen. It should be caught by the schemapack"
            + " spec validation."
        )
    return root_class_definition


def _should_embed(embedding_profile: EmbeddingProfile, relation_name: str) -> bool:
    """Function to decide whether to embed a relation based on the embedding profile.
    When a relation_name is not found in the profile, it returns True by default.
    If the profile is None, it returns True for all relations.
    If the profile is empty, it returns True for all relations.
    """
    if not embedding_profile:
        return True

    value = embedding_profile.get(relation_name)
    if value is None:
        return True

    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        return True

    raise InvalidEmbeddingProfileError(
        f"Invalid embedding profile: expected bool or dict for '{relation_name}', got {type(value).__name__}"
    )


def _get_next_embedding_profile(
    embedding_profile: EmbeddingProfile, relation_name: str
) -> EmbeddingProfile:
    """Function to get the next embedding profile for a relation."""
    if not embedding_profile:
        return None
    value = embedding_profile.get(relation_name)
    if isinstance(value, dict):
        return value
    return None


def _process_recursion(
    context: DenormalizationContext,
    class_name: ClassName,
    resource_ids: frozenset[ResourceId] | ResourceId | None,
) -> list[JsonObjectCompatible] | JsonObjectCompatible | None:
    """Function to process the recursion for denormalization."""
    if isinstance(resource_ids, frozenset):
        return [
            _recursive_denormalize(
                context,
                class_name,
                target_id,
            )
            for target_id in sorted(resource_ids)
        ]
    elif isinstance(resource_ids, str):
        return _recursive_denormalize(
            context,
            class_name,
            resource_ids,
        )
    else:
        return None


def _recursive_denormalize(
    context: DenormalizationContext,
    class_name: ClassName,
    resource_id: ResourceId,
):
    """Function used in recursively denormalize a resource by calling the function 'denormalize'."""
    if resource_id in context.resource_blacklist.get(class_name, set()):
        raise CircularRelationError(
            f"Cannot perform denormalization of datapack with circular relations. "
            f"The circular relation involved the resource with id {resource_id} of class {class_name}."
        )

    return denormalize(
        datapack=context.datapack,
        schemapack=context.schemapack,
        embedding_profile=context.embedding_profile,
        _resource_blacklist=context.resource_blacklist,
        _alt_root_class_name=class_name,
        _alt_root_resource_id=resource_id,
    )
