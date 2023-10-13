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

"""Logic for transforming metadata models."""

from copy import deepcopy
from typing import Union

from linkml_runtime.linkml_model.meta import ClassDefinition, SlotDefinition
from stringcase import snakecase

from metldata.builtin_transformations.custom_embeddings.embedding_profile import (
    EmbeddingProfile,
)
from metldata.model_utils.anchors import AnchorPoint, get_anchors_points_by_target
from metldata.model_utils.essentials import (
    ROOT_CLASS,
    ExportableSchemaView,
    MetadataModel,
)
from metldata.model_utils.identifiers import get_class_identifier
from metldata.model_utils.manipulate import (
    add_anchor_point,
    add_slot_usage_annotation,
    disable_identifier_slot,
    get_normalized_slot_usage,
)
from metldata.transform.base import MetadataModelTransformationError


def get_embedding_profile_root_slot(embedding_profile: EmbeddingProfile) -> str:
    """Get the root slot for an embedding profile."""
    return snakecase(embedding_profile.target_class)


def get_embedded_reference_slot(
    *,
    class_: ClassDefinition,
    schema_view: ExportableSchemaView,
    reference_slot_name: str,
    target: Union[str, EmbeddingProfile],
) -> SlotDefinition:
    """Update the slot definition of an embedded reference."""
    if not class_.slots or reference_slot_name not in class_.slots:
        raise MetadataModelTransformationError(
            f"Class '{class_.name}' does not have the slot '{reference_slot_name}'"
        )

    slot_usage = get_normalized_slot_usage(class_=class_)
    if reference_slot_name in slot_usage:
        slot_definition = slot_usage[reference_slot_name]
    else:
        slot_definition = SlotDefinition(name=reference_slot_name)

    # make sure that the range is in line with the embedding profile:
    expected_target_class = (
        target.source_class if isinstance(target, EmbeddingProfile) else target
    )
    induced_slot_definition = schema_view.induced_slot(
        slot_name=reference_slot_name, class_name=class_.name
    )
    if induced_slot_definition.range != expected_target_class:
        raise MetadataModelTransformationError(
            f"Range of slot '{reference_slot_name}' in class"
            + f" '{class_.name}' does not match the reference specified in the"
            + " embedding profile"
        )

    # update the range if the target is another embedded class:
    if isinstance(target, EmbeddingProfile):
        slot_definition.range = target.target_class

    # set the target slot to inlined:
    slot_definition.inlined = True
    if induced_slot_definition.multivalued:
        slot_definition.inlined_as_list = True

    return slot_definition


def generated_embedded_class(
    *,
    schema_view: ExportableSchemaView,
    embedding_profile: EmbeddingProfile,
) -> ClassDefinition:
    """Generate an embedded class from an embedding profile."""
    class_to_embed = schema_view.get_class(embedding_profile.source_class)
    if not class_to_embed:
        raise MetadataModelTransformationError(
            f"Could not find class {embedding_profile.source_class} in model"
        )

    embedded_class = deepcopy(class_to_embed)

    # rename the class:
    embedded_class.name = embedding_profile.target_class

    if not embedded_class.slots:
        embedded_class.slots = []

    if not embedded_class.slot_usage:
        embedded_class.slot_usage = {}

    embedded_class.slot_usage = get_normalized_slot_usage(class_=embedded_class)

    for (
        reference_slot_name,
        target,
    ) in embedding_profile.embedded_references.items():
        if reference_slot_name not in embedded_class.slots:
            raise MetadataModelTransformationError(
                f"Slot '{reference_slot_name}' not found in class"
                + f" '{embedding_profile.source_class}'."
            )

        embedded_class.slot_usage[reference_slot_name] = get_embedded_reference_slot(
            class_=class_to_embed,
            schema_view=schema_view,
            reference_slot_name=reference_slot_name,
            target=target,
        )

    return embedded_class


def add_anchor_point_for_embedded_class(
    *,
    schema_view: ExportableSchemaView,
    embedding_profile: EmbeddingProfile,
) -> ExportableSchemaView:
    """Add an anchor point for an embedded class to the schema view."""
    identifier_slot = get_class_identifier(
        model=schema_view.export_model(), class_name=embedding_profile.source_class
    )

    if not identifier_slot:
        raise MetadataModelTransformationError(
            f"Could not find identifier slot for class {embedding_profile.source_class}"
        )
    anchor_point = AnchorPoint(
        root_slot=get_embedding_profile_root_slot(embedding_profile=embedding_profile),
        target_class=embedding_profile.target_class,
        identifier_slot=identifier_slot,
    )

    schema_view = add_anchor_point(
        schema_view=schema_view,
        anchor_point=anchor_point,
        description=embedding_profile.description,
    )

    return schema_view


def add_custom_embedded_class(
    *,
    model: MetadataModel,
    embedding_profile: EmbeddingProfile,
    anchor_points_by_target: dict[str, AnchorPoint],
    include_anchor_point: bool = True,
) -> MetadataModel:
    """Add a custom embedded class to a metadata model.
    If no anchor point is needed, specify `include_anchor_point=False`.
    """
    schema_view = model.schema_view
    embedded_class = generated_embedded_class(
        schema_view=schema_view,
        embedding_profile=embedding_profile,
    )
    schema_view.add_class(embedded_class)

    # add anchor point for embedded class:
    if include_anchor_point:
        schema_view = add_anchor_point_for_embedded_class(
            schema_view=schema_view, embedding_profile=embedding_profile
        )
    else:
        schema_view = disable_identifier_slot(
            schema_view=schema_view, class_name=embedded_class.name
        )

    model_modified = schema_view.export_model()

    # also prepare embedded classes for references:
    for target in embedding_profile.embedded_references.values():
        if isinstance(target, EmbeddingProfile):
            model_modified = add_custom_embedded_class(
                model=model_modified,
                embedding_profile=target,
                anchor_points_by_target=anchor_points_by_target,
                include_anchor_point=False,
            )

    return model_modified


def mark_anchored_classes_as_hidden(
    *, model: MetadataModel, anchor_points_by_target: dict[str, AnchorPoint]
) -> MetadataModel:
    """Mark all classes that are anchored as hidden. Returns a copy of the model."""
    schema_view = model.schema_view

    for anchor_point in anchor_points_by_target.values():
        schema_view = add_slot_usage_annotation(
            schema_view=schema_view,
            slot_name=anchor_point.root_slot,
            class_name=ROOT_CLASS,
            annotation_key="hidden",
            annotation_value=True,
        )

    return schema_view.export_model()


def add_custom_embedded_classes(
    *, model: MetadataModel, embedding_profiles: list[EmbeddingProfile]
) -> MetadataModel:
    """Add custom embedded classes to a metadata model."""
    anchor_points_by_target = get_anchors_points_by_target(model=model)

    # mark all existing anchored classes as hidden, so that only the custom embedded
    # classes are visible:
    model = mark_anchored_classes_as_hidden(
        model=model, anchor_points_by_target=anchor_points_by_target
    )

    for embedding_profile in embedding_profiles:
        model = add_custom_embedded_class(
            model=model,
            embedding_profile=embedding_profile,
            anchor_points_by_target=anchor_points_by_target,
        )

    return model
