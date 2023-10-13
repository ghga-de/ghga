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

"""A transformation that normalizes a model to a canonical form."""

from metldata.builtin_transformations.normalize_model.config import NormalizationConfig
from metldata.builtin_transformations.normalize_model.model_transform import (
    normalize_model,
)
from metldata.custom_types import Json
from metldata.event_handling.models import SubmissionAnnotation
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import MetadataTransformer, TransformationDefinition


# pylint: disable=unused-argument
def check_model_assumptions(model: MetadataModel, config: NormalizationConfig):
    """Check that the classes and slots specified in the config exist in the model."""


# pylint: disable=unused-argument
def transform_model(model: MetadataModel, config: NormalizationConfig) -> MetadataModel:
    """Normalize the model."""
    return normalize_model(model)


class NormalizationTransformer(MetadataTransformer[NormalizationConfig]):
    """Transformer for normalizing the metadata model."""

    def transform(self, *, metadata: Json, annotation: SubmissionAnnotation) -> Json:
        """Transforms metadata.

        Args:
            metadata: The metadata to be transformed.
            annotation: The annotation on the metadata.

        Raises:
            MetadataTransformationError:
                if the transformation fails.
        """
        return metadata


NORMALIZATION_TRANSFORMATION = TransformationDefinition[NormalizationConfig](
    config_cls=NormalizationConfig,
    check_model_assumptions=check_model_assumptions,
    transform_model=transform_model,
    metadata_transformer_factory=NormalizationTransformer,
)
