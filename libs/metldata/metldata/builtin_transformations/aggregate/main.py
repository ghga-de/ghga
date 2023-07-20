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

from metldata.builtin_transformations.aggregate.config import AggregateConfig
from metldata.custom_types import Json
from metldata.event_handling.models import SubmissionAnnotation
from metldata.model_utils.assumptions import check_root_class_existence
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import MetadataTransformer, TransformationDefinition


class AggregateTransformer(MetadataTransformer[AggregateConfig]):
    """Transformer to create summary statistics from metadata."""

    def transform(self, *, metadata: Json, annotation: SubmissionAnnotation) -> Json:
        """Transforms metadata.

        Args:
            metadata: The metadata to be transformed.
            annotation: The annotation on the metadata.

        Raises:
            MetadataTransformationError:
                if the transformation fails.
        """
        return {}


def check_model_assumptions(
    model: MetadataModel,
    config: AggregateConfig,  # pylint: disable=unused-argument
) -> None:
    """Check the assumptions of the model.

    Raises:
        MetadataModelAssumptionError:
            if the model does not fulfill the assumptions.
    """
    check_root_class_existence(model=model)


# pylint: disable=unused-argument
def transform_model(model: MetadataModel, config: AggregateConfig) -> MetadataModel:
    """Transform the metadata model.

    Raises:
        MetadataModelTransformationError:
            if the transformation fails.
    """

    return model


AGGREGATE_TRANSFOMATION = TransformationDefinition[AggregateConfig](
    config_cls=AggregateConfig,
    check_model_assumptions=check_model_assumptions,
    transform_model=transform_model,
    metadata_transformer_factory=AggregateTransformer,
)
