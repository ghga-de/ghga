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

"""A tranformation for deleting slots from classes in a metadata model."""

from metldata.builtin_transformations.delete_slots.assumptions import (
    check_model_class_slots,
)
from metldata.builtin_transformations.delete_slots.config import SlotDeletionConfig
from metldata.builtin_transformations.delete_slots.metadata_transform import (
    delete_class_slots,
)
from metldata.builtin_transformations.delete_slots.model_transform import (
    delete_class_slots_from_model,
)
from metldata.event_handling.models import SubmissionAnnotation
from metldata.model_utils.anchors import get_anchors_points_by_target
from metldata.model_utils.assumptions import check_anchor_points
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import Json, MetadataTransformer, TransformationDefinition


def check_model_assumptions(model: MetadataModel, config: SlotDeletionConfig):
    """Check that the classes and slots specified in the config exist in the model."""
    check_model_class_slots(model=model, class_slots=config.slots_to_delete)
    check_anchor_points(model=model, classes=list(config.slots_to_delete))


def transform_model(model: MetadataModel, config: SlotDeletionConfig) -> MetadataModel:
    """Delete slots from classes in the model."""
    return delete_class_slots_from_model(
        model=model, class_slots=config.slots_to_delete
    )


class SlotDeletionMetadataTransformer(MetadataTransformer[SlotDeletionConfig]):
    """Transformer for deleting slots from classes in a metadata model."""

    def __init__(
        self,
        config: SlotDeletionConfig,
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
        return delete_class_slots(
            metadata=metadata,
            slots_to_delete=self._config.slots_to_delete,
            anchor_points_by_target=self._anchor_points_by_target,
        )


SLOT_DELETION_TRANSFORMATION = TransformationDefinition[SlotDeletionConfig](
    config_cls=SlotDeletionConfig,
    check_model_assumptions=check_model_assumptions,
    transform_model=transform_model,
    metadata_transformer_factory=SlotDeletionMetadataTransformer,
)
