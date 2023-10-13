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

"""A tranformation for merging multiple slots of a class into a single one."""

from metldata.builtin_transformations.merge_slots.assumptions import (
    check_model_class_slots,
)
from metldata.builtin_transformations.merge_slots.config import SlotMergingConfig
from metldata.builtin_transformations.merge_slots.metadata_transform import (
    apply_merge_instructions_to_metadata,
)
from metldata.builtin_transformations.merge_slots.model_transform import (
    merge_slots_in_model,
)
from metldata.event_handling.models import SubmissionAnnotation
from metldata.model_utils.anchors import get_anchors_points_by_target
from metldata.model_utils.assumptions import check_anchor_points
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import Json, MetadataTransformer, TransformationDefinition


def check_model_assumptions(model: MetadataModel, config: SlotMergingConfig):
    """Check that the classes and slots specified in the config exist in the model."""
    check_model_class_slots(model=model, merge_instructions=config.merge_instructions)

    classe_names = {
        merge_instruction.class_name for merge_instruction in config.merge_instructions
    }
    check_anchor_points(model=model, classes=list(classe_names))


def transform_model(model: MetadataModel, config: SlotMergingConfig) -> MetadataModel:
    """Merge slots of classes in the model."""
    return merge_slots_in_model(
        model=model, merge_instructions=config.merge_instructions
    )


class SlotMergingMetadataTransformer(MetadataTransformer[SlotMergingConfig]):
    """Transformer for merging slots of classes in a metadata model."""

    def __init__(
        self,
        config: SlotMergingConfig,
        original_model: MetadataModel,
        transformed_model: MetadataModel,
    ):
        """Initialize the transformer."""
        super().__init__(
            config=config,
            original_model=original_model,
            transformed_model=transformed_model,
        )

        self._anchor_points_by_target = get_anchors_points_by_target(
            model=self._original_model
        )

    def transform(self, *, metadata: Json, annotation: SubmissionAnnotation) -> Json:
        """Transforms metadata.

        Args:
            metadata: The metadata to be transformed.
            annotation: The annotation on the metadata.

        Raises:
            MetadataTransformationError:
                if the transformation fails.
        """
        return apply_merge_instructions_to_metadata(
            metadata=metadata,
            merge_instructions=self._config.merge_instructions,
            anchor_points_by_target=self._anchor_points_by_target,
        )


SLOT_MERGING_TRANSFORMATION = TransformationDefinition[SlotMergingConfig](
    config_cls=SlotMergingConfig,
    check_model_assumptions=check_model_assumptions,
    transform_model=transform_model,
    metadata_transformer_factory=SlotMergingMetadataTransformer,
)
