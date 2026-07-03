# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Logic for resolving reference paths for existing metadata."""

from collections import defaultdict

from metldata.builtin_transformations.infer_references.path.path import ReferencePath
from metldata.builtin_transformations.infer_references.path.path_elements import (
    ReferencePathElement,
    ReferencePathElementType,
)
from metldata.custom_types import Json
from metldata.metadata_utils import (
    ForeignIdLookUpError,
    MetadataResourceNotFoundError,
    SelfIdLookUpError,
    index_resources_by_id,
    lookup_foreign_ids,
    lookup_self_id,
)
from metldata.model_utils.anchors import (
    AnchorPoint,
    AnchorPointNotFoundError,
    lookup_anchor_point,
)


class PathElementResolutionError(RuntimeError):
    """Raised when a path element cannot be resolved."""


class ResolutionIndex:
    """Per-metadata-snapshot indexes that make reference resolution O(1) per lookup.

    Reference resolution otherwise scans an entire class for every id lookup and, for
    passive path elements, scans all candidate resources for every source resource -
    making inference O(N^2) in the size of a class. This builds, lazily and at most once
    per class / per (class, slot), an id->resource map and a reverse map of
    back-references, turning those scans into dictionary lookups.

    The index references resources directly out of ``global_metadata`` (no copies) and
    is therefore only valid while that metadata is unchanged - i.e. for the resolution
    of a single inferred reference. The resolved resources are read-only.
    """

    def __init__(
        self,
        *,
        global_metadata: Json,
        anchor_points_by_target: dict[str, AnchorPoint],
    ):
        self._global_metadata = global_metadata
        self._anchor_points = anchor_points_by_target
        self._by_id: dict[str, dict[str, Json]] = {}
        self._back: dict[tuple[str, str], dict[str, set[str]]] = {}

    def resource_by_id(self, *, class_name: str, identifier: str) -> Json:
        """Return the resource of the given class with the given identifier.

        Raises:
            MetadataResourceNotFoundError: if the resource could not be found.
        """
        index = self._by_id.get(class_name)
        if index is None:
            index = index_resources_by_id(
                class_name=class_name,
                global_metadata=self._global_metadata,
                anchor_points_by_target=self._anchor_points,
            )
            self._by_id[class_name] = index

        try:
            return index[identifier]
        except KeyError as error:
            raise MetadataResourceNotFoundError(
                f"Could not find resource with identifier '{identifier}' of class"
                + f" '{class_name}' in the global metadata."
            ) from error

    def back_referencing_ids(
        self, *, target_class: str, slot: str
    ) -> dict[str, set[str]]:
        """Map each id referenced via ``slot`` on resources of ``target_class`` to the
        set of those resources' own identifiers.

        Raises:
            PathElementResolutionError: if the target class cannot be resolved.
        """
        key = (target_class, slot)
        index = self._back.get(key)
        if index is not None:
            return index

        try:
            target_anchor_point = lookup_anchor_point(
                class_name=target_class, anchor_points_by_target=self._anchor_points
            )
        except AnchorPointNotFoundError as error:
            raise PathElementResolutionError(
                "Cannot resolve path element because of a missing anchor point for"
                + f" target class '{target_class}'."
            ) from error

        target_resources = self._global_metadata.get(target_anchor_point.root_slot)
        if target_resources is None:
            raise PathElementResolutionError(
                "Cannot resolve path element: No target resources found for"
                + f" root slot '{target_anchor_point.root_slot}'."
            )

        index = defaultdict(set)
        for target_resource in target_resources:
            target_id = lookup_self_id(
                resource=target_resource,
                identifier_slot=target_anchor_point.identifier_slot,
            )
            for source_id in lookup_foreign_ids(resource=target_resource, slot=slot):
                index[source_id].add(target_id)

        self._back[key] = index
        return index


def resolve_target_ids_active_element(
    *, source_resource: Json, path_element: ReferencePathElement
) -> set[str]:
    """Resolve an active reference path element applied to a metadata resource.

    Args:
        source_resource: The metadata resource to which the path element is applied.
        path_element: The active path element to resolve.

    Returns:
        A list of target IDs that are targeted by the path element in context of the
        provided source resource.

    Raises:
        PathElementResolutionError:
            if the path element cannot be resolved.
    """
    if path_element.type_ != ReferencePathElementType.ACTIVE:
        raise ValueError("Passive path element supplied where active expected.")

    try:
        target_ids = lookup_foreign_ids(
            resource=source_resource, slot=path_element.slot
        )
    except ForeignIdLookUpError as error:
        raise PathElementResolutionError(
            "Failed to resolve the path element applied to the"
            + f" resource '{source_resource}': {error}"
        ) from error

    return target_ids


def resolve_target_ids_passive_element(
    *,
    source_resource: Json,
    path_element: ReferencePathElement,
    index: ResolutionIndex,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> set[str]:
    """Resolve a passive reference path element applied to a metadata resource.

    Args:
        source_resource: The metadata resource to which the path element is applied.
        path_element: The passive path element to resolve.
        index: The resolution index for the current metadata snapshot.
        anchor_points_by_target: The anchor points by target class.

    Returns:
        A list of target IDs that are targeted by the path element in context of the
        provided source resource.

    Raises:
        PathElementResolutionError:
            if the path element cannot be resolved.
    """
    if path_element.type_ != ReferencePathElementType.PASSIVE:
        raise ValueError("Active path element supplied where passive expected.")

    try:
        source_anchor_point = lookup_anchor_point(
            class_name=path_element.source,
            anchor_points_by_target=anchor_points_by_target,
        )
    except AnchorPointNotFoundError as error:
        raise PathElementResolutionError(
            "Cannot resolve path element because of a missing anchor point for"
            + f" source class '{path_element.source}'."
        ) from error

    try:
        source_identifier = lookup_self_id(
            resource=source_resource,
            identifier_slot=source_anchor_point.identifier_slot,
        )
    except SelfIdLookUpError as error:
        raise PathElementResolutionError(
            f"Cannot resolve path element: '{error}'"
        ) from error

    # Resources of the target class reference source ids via path_element.slot; use the
    # precomputed reverse index to find, in O(1), which target resources reference this
    # source - instead of rescanning the whole target class for every source resource.
    back_references = index.back_referencing_ids(
        target_class=path_element.target, slot=path_element.slot
    )

    return set(back_references.get(source_identifier, ()))


def resolve_path_element(
    *,
    source_resource: Json,
    index: ResolutionIndex,
    path_element: ReferencePathElement,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> list[Json]:
    """Resolve a reference path element applied to a metadata resource.

    Returns:
        A list of metadata resources that are targeted by the path element.

    Raises:
        PathElementResolutionError:
            if the path element cannot be resolved.
    """
    if path_element.type_ == ReferencePathElementType.ACTIVE:
        target_ids = resolve_target_ids_active_element(
            source_resource=source_resource, path_element=path_element
        )
    else:
        target_ids = resolve_target_ids_passive_element(
            source_resource=source_resource,
            path_element=path_element,
            index=index,
            anchor_points_by_target=anchor_points_by_target,
        )

    if not target_ids:
        return []

    target_resources: list[Json] = []
    for target_id in target_ids:
        try:
            target_resource = index.resource_by_id(
                class_name=path_element.target,
                identifier=target_id,
            )
        except MetadataResourceNotFoundError as error:
            raise PathElementResolutionError(
                f"Cannot resolve path element for source resource '{source_resource}'"
                + f" because the target resource with ID '{target_id}' could not be"
                + " found."
            ) from error
        target_resources.append(target_resource)

    return target_resources


def resolve_reference_for_metadata_resource(
    *,
    resource: Json,
    global_metadata: Json,
    reference_path: ReferencePath,
    anchor_points_by_target: dict[str, AnchorPoint],
    index: ResolutionIndex | None = None,
) -> list[Json]:
    """Resolve an inferred reference for an individual metadata resource.

    Args:
        resource: The metadata resource to resolve the reference for.
        global_metadata: The global metadata context to look up references in.
        reference_path: The path of the inferred reference.
        anchor_points: The anchor points of the metadata model.
        index:
            A resolution index for ``global_metadata``. When resolving the same
            reference for many resources, build the index once and pass it in to avoid
            rebuilding it per resource. If omitted, a fresh index is built (valid since
            ``global_metadata`` is only read here).

    Returns:
        A list of metadata resources that are targeted by the reference.

    Raises:
        PathElementResolutionError:
            if the reference resolution fails.
    """
    if index is None:
        index = ResolutionIndex(
            global_metadata=global_metadata,
            anchor_points_by_target=anchor_points_by_target,
        )

    source_resources = [resource]
    for path_element in reference_path.elements:
        target_resources: list[Json] = []
        for source_resource in source_resources:
            local_target_resources = resolve_path_element(
                source_resource=source_resource,
                index=index,
                path_element=path_element,
                anchor_points_by_target=anchor_points_by_target,
            )
            target_resources.extend(local_target_resources)

        # set the target resources of the current path element as the source resources
        # for the next path element:
        source_resources = target_resources

    return source_resources
