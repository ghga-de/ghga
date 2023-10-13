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

"""Logic for transforming metadata."""


from metldata.builtin_transformations.infer_references.path.resolve import (
    resolve_reference_for_metadata_resource,
)
from metldata.builtin_transformations.infer_references.reference import (
    InferredReference,
)
from metldata.metadata_utils import (
    SelfIdLookUpError,
    get_resources_of_class,
    lookup_self_id,
    upsert_resources_in_metadata,
)
from metldata.model_utils.anchors import (
    AnchorPoint,
    AnchorPointNotFoundError,
    lookup_anchor_point,
)
from metldata.transform.base import (
    Json,
    MetadataModelTransformationError,
    MetadataTransformationError,
)


def add_reference_to_metadata_resource(
    resource: Json,
    global_metadata: Json,
    reference: InferredReference,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> Json:
    """Add an inferred reference to an individual metadata resource.

    Args:
        resource: The metadata resource to modify.
        global_metadata: The global metadata context to look up references in.
        reference: The inferred reference.
        anchor_points: The anchor points of the metadata model.

    Raises:
        MetadataTransformationError:
            if the transformation of the metadata fails.
    """
    try:
        target_anchor_point = lookup_anchor_point(
            class_name=reference.target, anchor_points_by_target=anchor_points_by_target
        )
    except AnchorPointNotFoundError as error:
        raise MetadataModelTransformationError(
            f"Cannot add reference '{reference}' to metadata resource '{resource}'"
            + " because the target anchor point could not be found."
        ) from error

    if reference.new_slot in resource:
        raise MetadataModelTransformationError(
            f"Cannot add reference '{reference}' to metadata resource '{resource}'"
            + f" because the target slot '{reference.new_slot}' already exists."
        )

    target_resources = resolve_reference_for_metadata_resource(
        resource=resource,
        global_metadata=global_metadata,
        reference_path=reference.path,
        anchor_points_by_target=anchor_points_by_target,
    )

    # get IDs of final target resources:
    target_ids: set[str] = set()
    for target_resource in target_resources:
        try:
            target_ids.add(
                lookup_self_id(
                    resource=target_resource,
                    identifier_slot=target_anchor_point.identifier_slot,
                )
            )
        except SelfIdLookUpError as error:
            raise MetadataTransformationError(
                f"Cannot add reference '{reference}' to metadata resource '{resource}'"
                + f" because the target resource '{target_resource}' does not have"
                + f" an identifier in slot '{target_anchor_point.identifier_slot}'."
            ) from error

    # add the target IDs to the source resource:
    resource_copy = resource.copy()
    resource_copy[reference.new_slot] = sorted(target_ids)

    return resource_copy


def add_reference_to_metadata(
    *,
    metadata: Json,
    reference: InferredReference,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> Json:
    """Transform metadata by adding an inferred reference.

    Raises:
            MetadataTransformationError:
                if the transformation of the metadata fails.
    """
    resources = get_resources_of_class(
        global_metadata=metadata,
        class_name=reference.source,
        anchor_points_by_target=anchor_points_by_target,
    )

    modified_resources = [
        add_reference_to_metadata_resource(
            resource=resource,
            global_metadata=metadata,
            reference=reference,
            anchor_points_by_target=anchor_points_by_target,
        )
        for resource in resources
    ]

    return upsert_resources_in_metadata(
        resources=modified_resources,
        class_name=reference.source,
        global_metadata=metadata,
        anchor_points_by_target=anchor_points_by_target,
    )


def add_references_to_metadata(
    *,
    metadata: Json,
    references: list[InferredReference],
    anchor_points_by_target: dict[str, AnchorPoint],
) -> Json:
    """Transform metadata and return the transformed one.

    Raises:
        MetadataTransformationError:
            if the transformation of the metadata fails.
    """
    for reference in references:
        metadata = add_reference_to_metadata(
            metadata=metadata,
            reference=reference,
            anchor_points_by_target=anchor_points_by_target,
        )

    return metadata
