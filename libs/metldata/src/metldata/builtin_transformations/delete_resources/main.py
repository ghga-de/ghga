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

"""A transformation for deleting resources and the references to them."""

from metldata.builtin_transformations.delete_resources.assumptions import (
    check_model_assumptions,
)
from metldata.builtin_transformations.delete_resources.config import (
    ResourceDeletionConfig,
)
from metldata.builtin_transformations.delete_resources.metadata_transform import (
    delete_resources,
)
from metldata.event_handling.models import SubmissionAnnotation
from metldata.model_utils.anchors import get_anchors_points_by_target
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import Json, MetadataTransformer, TransformationDefinition


def transform_model(
    model: MetadataModel, config: ResourceDeletionConfig
) -> MetadataModel:
    """Return the model unchanged, since only resources are deleted."""
    return model


class ResourceDeletionMetadataTransformer(MetadataTransformer[ResourceDeletionConfig]):
    """Transformer for deleting resources and the references to them."""

    def __init__(
        self,
        config: ResourceDeletionConfig,
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
        return delete_resources(
            metadata=metadata,
            resources_to_delete=self._config.resources_to_delete,
            anchor_points_by_target=self._anchor_points_by_target,
            schema_view=self._original_model.schema_view,
        )


RESOURCE_DELETION_TRANSFORMATION = TransformationDefinition[ResourceDeletionConfig](
    config_cls=ResourceDeletionConfig,
    check_model_assumptions=check_model_assumptions,
    transform_model=transform_model,
    metadata_transformer_factory=ResourceDeletionMetadataTransformer,
)
