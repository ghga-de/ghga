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

"""A transformation to infer references based on existing ones in the metadata model."""

from metldata.builtin_transformations.infer_references.config import (
    ReferenceInferenceConfig,
)
from metldata.builtin_transformations.infer_references.metadata_transform import (
    add_references_to_metadata,
)
from metldata.builtin_transformations.infer_references.model_transform import (
    add_references_to_model,
)
from metldata.model_utils.assumptions import check_basic_model_assumption
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import Json, MetadataTransformer, TransformationDefinition


class ReferenceInferenceMetadataTransformer(
    MetadataTransformer[ReferenceInferenceConfig]
):
    """A transformer that infers references in metadata based on existing once."""

    def transform(self, *, metadata: Json) -> Json:
        """Transforms metadata.

        Raises:
            MetadataTransformationError:
                if the transformation fails.
        """

        return add_references_to_metadata(
            metadata=metadata,
            model=self._original_model,
            references=self._config.inferred_references,
        )


def check_model_assumptions(
    model: MetadataModel,
    config: ReferenceInferenceConfig,  # pylint: disable=unused-argument
) -> None:
    """Check the assumptions of the model.

    Raises:
        MetadataModelAssumptionError:
            if the model does not fulfill the assumptions.
    """

    check_basic_model_assumption(model=model)


def transform_model(
    model: MetadataModel, config: ReferenceInferenceConfig
) -> MetadataModel:
    """Transform the metadata model.

    Raises:
        MetadataModelTransformationError:
            if the transformation fails.
    """

    return add_references_to_model(
        model=model,
        references=config.inferred_references,
    )


reference_inference_transformation = TransformationDefinition[ReferenceInferenceConfig](
    config=ReferenceInferenceConfig,
    check_model_assumptions=check_model_assumptions,
    transform_model=transform_model,
    metadata_transformer_factory=ReferenceInferenceMetadataTransformer,
)
