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

"""Core functionality for aggregate transformations."""

from metldata.builtin_transformations.aggregate.cached_model import CachedMetadataModel
from metldata.builtin_transformations.aggregate.config import AggregateConfig
from metldata.builtin_transformations.aggregate.metadata_transform import (
    execute_aggregations,
)
from metldata.builtin_transformations.aggregate.model_transform import (
    build_aggregation_model,
)
from metldata.custom_types import Json
from metldata.event_handling.models import SubmissionAnnotation
from metldata.model_utils.assumptions import check_basic_model_assumption
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import MetadataTransformer, TransformationDefinition


class AggregateTransformer(MetadataTransformer[AggregateConfig]):
    """Transformer to create summary statistics from metadata."""

    def __init__(
        self,
        config: AggregateConfig,
        original_model: MetadataModel,
        transformed_model: MetadataModel,
    ):
        """Initialize the transformer."""
        super().__init__(
            config=config,
            original_model=original_model,
            transformed_model=transformed_model,
        )

        self._original_cached_model = CachedMetadataModel(model=self._original_model)
        self._transformed_cached_model = CachedMetadataModel(
            model=self._transformed_model
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
        return execute_aggregations(
            original_model=self._original_cached_model,
            transformed_anchors_points=self._transformed_cached_model.anchors_points_by_target,
            metadata=metadata,
            aggregations=self._config.aggregations,
        )


def check_model_assumptions(
    model: MetadataModel,
    config: AggregateConfig,  # pylint: disable=unused-argument
) -> None:
    """Check the assumptions of the model.

    Raises:
        MetadataModelAssumptionError:
            if the model does not fulfill the assumptions.
    """
    check_basic_model_assumption(model=model)


def transform_model(model: MetadataModel, config: AggregateConfig) -> MetadataModel:
    """Transform the metadata model.

    Raises:
        MetadataModelTransformationError:
            if the transformation fails.
    """
    return build_aggregation_model(model=model, config=config)


AGGREGATE_TRANSFORMATION = TransformationDefinition[AggregateConfig](
    config_cls=AggregateConfig,
    check_model_assumptions=check_model_assumptions,
    transform_model=transform_model,
    metadata_transformer_factory=AggregateTransformer,
)
