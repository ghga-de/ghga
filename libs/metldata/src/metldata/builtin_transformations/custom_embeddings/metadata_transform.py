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

from typing import Union, cast

from metldata.builtin_transformations.custom_embeddings.embedding_profile import (
    EmbeddingProfile,
)
from metldata.builtin_transformations.custom_embeddings.model_transform import (
    get_embedding_profile_root_slot,
)
from metldata.metadata_utils import (
    MetadataResourceNotFoundError,
    get_resource_dict_of_class,
    lookup_resource_by_identifier,
    upsert_resources_in_metadata,
)
from metldata.model_utils.anchors import AnchorPoint, lookup_anchor_point
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import Json, MetadataTransformationError


def is_slot_multivalued(
    *, slot_name: str, class_name: str, model: MetadataModel
) -> bool:
    """Checks whether a slot is multivalued."""
    slot_definition = model.schema_view.induced_slot(
        slot_name=slot_name, class_name=class_name
    )

    if not slot_definition:
        raise RuntimeError(  # this should never happen
            f"Slot '{slot_name}' not found in class '{class_name}'"
        )

    return bool(slot_definition.multivalued)


def resolve_target_resource(
    target_resource_id: str,
    target: Union[str, EmbeddingProfile],
    global_metadata: Json,
    model: MetadataModel,
    anchor_points_by_target: dict,
) -> Json:
    """Resolves a target resource.

    Raises:
        MetadataTransformationError: If the target resource could not be found.
    """
    if isinstance(target, EmbeddingProfile):
        return generate_embedded_resource(
            resource_id=target_resource_id,
            embedding_profile=target,
            global_metadata=global_metadata,
            model=model,
            anchor_points_by_target=anchor_points_by_target,
        )

    try:
        return lookup_resource_by_identifier(
            class_name=target,
            identifier=target_resource_id,
            global_metadata=global_metadata,
            anchor_points_by_target=anchor_points_by_target,
        )
    except MetadataResourceNotFoundError as error:
        raise MetadataTransformationError(
            f"Could not find resource '{target_resource_id}' of class '{target}'"
        ) from error


def generate_embedded_resource(
    resource_id: str,
    embedding_profile: EmbeddingProfile,
    global_metadata: Json,
    model: MetadataModel,
    anchor_points_by_target: dict,
) -> Json:
    """Generates an embedded version of the specified resource. This is done recursively
    for all embedded references that are linked to this resource.
    """
    resource = lookup_resource_by_identifier(
        class_name=embedding_profile.source_class,
        identifier=resource_id,
        global_metadata=global_metadata,
        anchor_points_by_target=anchor_points_by_target,
    )

    for reference_slot_name, target in embedding_profile.embedded_references.items():
        if is_slot_multivalued(
            slot_name=reference_slot_name,
            class_name=embedding_profile.source_class,
            model=model,
        ):
            target_resource_ids = cast(list[str], resource[reference_slot_name])
            target_resources = [
                resolve_target_resource(
                    target_resource_id=target_resource_id,
                    target=target,
                    global_metadata=global_metadata,
                    model=model,
                    anchor_points_by_target=anchor_points_by_target,
                )
                for target_resource_id in target_resource_ids
            ]
            resource[reference_slot_name] = target_resources
        else:
            target_resource_id = cast(str, resource[reference_slot_name])
            target_resource = resolve_target_resource(
                target_resource_id=target_resource_id,
                target=target,
                global_metadata=global_metadata,
                model=model,
                anchor_points_by_target=anchor_points_by_target,
            )
            resource[reference_slot_name] = target_resource

    return resource


def add_custom_embedding_to_metadata(
    *,
    metadata: Json,
    embedding_profile: EmbeddingProfile,
    model: MetadataModel,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> Json:
    """Add custom embedding to the metadata.

    Raises:
        MetadataTransformationError:
            if the transformation of the metadata fails.
    """
    resource_ids = get_resource_dict_of_class(
        class_name=embedding_profile.source_class,
        global_metadata=metadata,
        anchor_points_by_target=anchor_points_by_target,
    ).keys()

    resources = [
        generate_embedded_resource(
            resource_id=resource_id,
            embedding_profile=embedding_profile,
            global_metadata=metadata,
            model=model,
            anchor_points_by_target=anchor_points_by_target,
        )
        for resource_id in resource_ids
    ]

    # add anchor point for embedding profile:
    source_class_anchor_point = lookup_anchor_point(
        class_name=embedding_profile.source_class,
        anchor_points_by_target=anchor_points_by_target,
    )
    embedded_class_anchor_point = AnchorPoint(
        target_class=embedding_profile.target_class,
        identifier_slot=source_class_anchor_point.identifier_slot,
        root_slot=get_embedding_profile_root_slot(embedding_profile=embedding_profile),
    )
    anchor_points_by_target_modified = anchor_points_by_target.copy()
    anchor_points_by_target_modified[
        embedding_profile.target_class
    ] = embedded_class_anchor_point

    return upsert_resources_in_metadata(
        resources=resources,
        class_name=embedding_profile.target_class,
        global_metadata=metadata,
        anchor_points_by_target=anchor_points_by_target_modified,
    )


def add_custom_embeddings_to_metadata(
    *,
    metadata: Json,
    embedding_profiles: list[EmbeddingProfile],
    model: MetadataModel,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> Json:
    """Add custom embeddings to the metadata.

    Raises:
        MetadataTransformationError:
            if the transformation of the metadata fails.
    """
    for embedding_profile in embedding_profiles:
        metadata = add_custom_embedding_to_metadata(
            metadata=metadata,
            embedding_profile=embedding_profile,
            model=model,
            anchor_points_by_target=anchor_points_by_target,
        )

    return metadata
