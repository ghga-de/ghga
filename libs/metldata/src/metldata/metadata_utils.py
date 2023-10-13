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

"""Utilities for handling metadata."""

from copy import deepcopy
from typing import Union, cast

from metldata.custom_types import Json
from metldata.model_utils.anchors import AnchorPoint, lookup_anchor_point


class SelfIdLookUpError(RuntimeError):
    """Raised when the self id cannot be looked up."""


class ForeignIdLookUpError(RuntimeError):
    """Raised when a foreign id cannot be looked up."""


class MetadataAnchorMismatchError(RuntimeError):
    """Raised when the provided metadata does not match the expected anchor points."""


class MetadataResourceNotFoundError(RuntimeError):
    """Raised when a resource could not be found in the metadata."""


class IdenitifierConflictError(RuntimeError):
    """Raised when multiple resources of the same class with the same identifier exist."""


class SlotNotFoundError(RuntimeError):
    """Raised when a slot cannot be found in a Metadata Resource."""


def lookup_self_id(*, resource: Json, identifier_slot: str):
    """Lookup the ID of the specified resource."""
    self_id = resource.get(identifier_slot)

    if self_id is None:
        raise SelfIdLookUpError(
            "Cannot lookup the identifier because the corresponding slot"
            + f" '{identifier_slot}' is not present in the resource '{resource}'."
        )

    if not isinstance(self_id, str):
        raise SelfIdLookUpError(
            f"Cannot lookup the identifier because the slot '{identifier_slot}' of"
            + f" resource '{resource}' contains a non-string value."
        )

    return self_id


def lookup_foreign_ids(*, resource: Json, slot: str) -> set[str]:
    """Lookup foreign IDs referenced by the specified resource using the specified
    slot.
    """
    foreign_ids = resource.get(slot)

    if foreign_ids is None:
        raise ForeignIdLookUpError(
            f"Cannot lookup foreign IDs because the slot '{slot}' is not present"
            + f" in the resource '{resource}'."
        )

    # convert single value to list:
    if not isinstance(foreign_ids, list):
        foreign_ids = [foreign_ids]

    # check that all values are strings:
    if not all(isinstance(value, str) for value in foreign_ids):
        raise ForeignIdLookUpError(
            f"Cannot lookup foreign IDs because the slot '{slot}' of resource"
            + f" '{resource}' contains non-string values."
        )

    foreign_ids = set(foreign_ids)
    foreign_ids = cast(set[str], foreign_ids)

    return foreign_ids


def lookup_resource_by_identifier(
    *,
    class_name: str,
    identifier: str,
    global_metadata: Json,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> Json:
    """Lookup a resource of the given class in the provided global metadata by its
    identifier.

    Raises:
        MetadataAnchorMismatchError:
            if the provided metadata does not match the expected anchor points.
        MetadataResourceNotFoundError:
            if the resource with the given identifier could not be found.
    """
    anchor_point = lookup_anchor_point(
        class_name=class_name, anchor_points_by_target=anchor_points_by_target
    )

    if anchor_point.root_slot not in global_metadata:
        raise MetadataAnchorMismatchError(
            f"Could not find root slot of the anchor point '{anchor_point.root_slot}'"
            + " in the global metadata."
        )

    resources = global_metadata[anchor_point.root_slot]

    resources_dict = convert_resource_list_to_dict(
        resources=resources, identifier_slot=anchor_point.identifier_slot
    )

    if identifier not in resources_dict:
        raise MetadataResourceNotFoundError(
            f"Could not find resource with identifier '{identifier}' of class"
            + f" '{class_name}' in the global metadata."
        )

    target_resource = resources_dict[identifier]

    return target_resource


def check_identifier_uniqueness(*, resources: list[Json], identifier_slot: str) -> None:
    """Check if the identifiers of the specified resources are unique.

    Raises:
        IdenitifierConflictError:
            if the identifiers are not unique.
    """
    identifiers = [resource[identifier_slot] for resource in resources]

    if len(identifiers) != len(set(identifiers)):
        raise IdenitifierConflictError(
            "The identifiers of the resources are not unique."
        )


def convert_list_to_inlined_dict(
    *, resources: list[Json], identifier_slot: str
) -> dict[str, Json]:
    """Convert a list of resources of same type into a dictionary representation, i.e.
    to "inlined_as_list=false" format.

    Raises:
        IdenitifierConflictError:
            if the identifiers are not unique.
    """
    check_identifier_uniqueness(resources=resources, identifier_slot=identifier_slot)

    return {
        lookup_self_id(resource=resource, identifier_slot=identifier_slot): {
            slot: deepcopy(resource[slot])
            for slot in resource
            if slot != identifier_slot
        }
        for resource in resources
    }


def convert_inlined_dict_to_list(
    *, resources: dict[str, Json], identifier_slot: str
) -> list[Json]:
    """Convert a dictionary representation of resources into a list representation, i.e.
    to "inlined_as_list=true" format.
    """
    resource_copy = deepcopy(resources)

    return [
        {identifier_slot: identifier, **resource_copy}
        for identifier, resource in resource_copy.items()
    ]


def convert_resource_list_to_dict(
    *, resources: list[Json], identifier_slot: str
) -> dict[str, Json]:
    """Convert a list of resources of same type into a dictionary representation.
    Unlike the `inlined_as_list=false` structure from LinkML, the dict will contain
    resources with identifier slots.
    """
    return {
        lookup_self_id(resource=resource, identifier_slot=identifier_slot): deepcopy(
            resource
        )
        for resource in resources
    }


def get_resources_of_class(
    *,
    class_name: str,
    global_metadata: Json,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> list[Json]:
    """Get all instances of the given class from the provided global metadata.

    Raises:
        MetadataAnchorMismatchError:
            if the provided metadata does not match the expected anchor points.
    """
    anchor_point = lookup_anchor_point(
        class_name=class_name, anchor_points_by_target=anchor_points_by_target
    )

    if anchor_point.root_slot not in global_metadata:
        raise MetadataAnchorMismatchError(
            f"Could not find root slot of the anchor point '{anchor_point.root_slot}'"
            + " in the global metadata."
        )

    return deepcopy(global_metadata[anchor_point.root_slot])


def get_resource_dict_of_class(
    *,
    class_name: str,
    global_metadata: Json,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> dict[str, Json]:
    """Get all instances as dict of the given class from the provided global metadata.
    Unlike the `inlined_as_list=false` structure from LinkML, the dict will contain
    resources with identifier slots.

    Raises:
        MetadataAnchorMismatchError:
            if the provided metadata does not match the expected anchor points.
    """
    resources = get_resources_of_class(
        class_name=class_name,
        global_metadata=global_metadata,
        anchor_points_by_target=anchor_points_by_target,
    )

    anchor_point = lookup_anchor_point(
        class_name=class_name, anchor_points_by_target=anchor_points_by_target
    )

    return convert_resource_list_to_dict(
        resources=resources, identifier_slot=anchor_point.identifier_slot
    )


def upsert_resources_in_metadata(
    *,
    resources: list[Json],
    class_name: str,
    global_metadata: Json,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> Json:
    """Update the provided global metadata with the provided resources of the given
    class. If the anchor point for the given class does not yet exist, it is created.
    Returns a copy of the updated metadata.
    """
    anchor_point = lookup_anchor_point(
        class_name=class_name, anchor_points_by_target=anchor_points_by_target
    )

    global_metadata_copy = deepcopy(global_metadata)

    return {**global_metadata_copy, anchor_point.root_slot: resources}


def lookup_slot_in_resource(
    *, resource: Json, slot_name: str
) -> Union[Json, list[Json]]:
    """Lookup a slot in a resource. Raises an error if the slot does not exist."""
    content = resource.get(slot_name)

    if content is None:
        raise SlotNotFoundError(
            f"Could not find slot '{slot_name}' in resource: {resource}"
        )

    return content
