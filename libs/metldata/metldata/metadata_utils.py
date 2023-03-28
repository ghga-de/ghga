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

from typing import cast

from metldata.custom_types import Json
from metldata.model_utils.anchors import AnchorPoint


class SelfIdLookUpError(RuntimeError):
    """Raised when the self id cannot be looked up."""


class ForeignIdLookUpError(RuntimeError):
    """Raised when a foreign id cannot be looked up."""


class MetadataAnchorMismatchError(RuntimeError):
    """Raised when the provided metadata does not match the expected anchor points."""


class MetadataResourceNotFoundError(RuntimeError):
    """Raised when a resource could not be found in the metadata."""


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
    slot."""

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


def add_identifier_to_anchored_resource(
    *,
    resource: Json,
    identifier: str,
    identifier_slot: str,
) -> Json:
    """Anchored resources have no identifier slot. This function adds the identifier."""

    return {**resource, identifier_slot: identifier}


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
        MetadataAnchorMissmatchError:
            if the provided metadata does not match the expected anchor points.
        MetadataResourceNotFoundError:
            if the resource with the given identifier could not be found.
    """

    anchor_point = anchor_points_by_target[class_name]

    if anchor_point.root_slot not in global_metadata:
        raise MetadataAnchorMismatchError(
            f"Could not find root slot of the anchor point '{anchor_point.root_slot}'"
            + " in the global metadata."
        )

    resources = global_metadata[anchor_point.root_slot]

    if identifier not in resources:
        raise MetadataResourceNotFoundError(
            f"Could not find resource with identifier '{identifier}' of class"
            + f" '{class_name}' in the global metadata."
        )

    target_resource = resources[identifier]

    return add_identifier_to_anchored_resource(
        resource=target_resource,
        identifier=identifier,
        identifier_slot=anchor_point.identifier_slot,
    )


def convert_list_to_inlined_dict(
    *, resources: list[Json], identifier_slot: str
) -> dict[str, Json]:
    """Convert a list of resources of same type into a dictionary representation, i.e.
    to "inlined_as_list=false" format."""

    return {
        resource[identifier_slot]: {
            slot: resource[slot] for slot in resource if slot != identifier_slot
        }
        for resource in resources
    }
