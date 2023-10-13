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

"""A transformation to add accessions to metadata."""

from metldata.builtin_transformations.add_accessions.config import (
    AccessionAdditionConfig,
)
from metldata.builtin_transformations.add_accessions.metadata_transform import (
    add_accessions_to_metadata,
    get_references,
)
from metldata.builtin_transformations.add_accessions.model_transform import (
    add_accessions_to_model,
)
from metldata.event_handling.models import SubmissionAnnotation
from metldata.model_utils.anchors import get_anchors_points_by_target
from metldata.model_utils.assumptions import check_basic_model_assumption
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import Json, MetadataTransformer, TransformationDefinition


class AccessionAdditionMetadataTransformer(
    MetadataTransformer[AccessionAdditionConfig]
):
    """A transformer to add accessions to metadata."""

    def __init__(
        self,
        config: AccessionAdditionConfig,
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
        self._references = get_references(
            metadata_model=self._original_model,
            anchor_points_by_target=self._anchor_points_by_target,
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
        return add_accessions_to_metadata(
            metadata=metadata,
            accession_slot_name=self._config.accession_slot_name,
            accession_map=annotation.accession_map,
            references=self._references,
            anchor_points_by_target=self._anchor_points_by_target,
        )


def check_model_assumptions(
    model: MetadataModel,
    config: AccessionAdditionConfig,  # pylint: disable=unused-argument
) -> None:
    """Check the assumptions of the model.

    Raises:
        MetadataModelAssumptionError:
            if the model does not fulfill the assumptions.
    """
    check_basic_model_assumption(model=model)


def transform_model(
    model: MetadataModel, config: AccessionAdditionConfig
) -> MetadataModel:
    """Transform the metadata model.

    Raises:
        MetadataModelTransformationError:
            if the transformation fails.
    """
    return add_accessions_to_model(
        model=model,
        accession_slot_name=config.accession_slot_name,
        accession_slot_description=config.accession_slot_description,
    )


ACCESSION_ADDITION_TRANSFORMATION = TransformationDefinition[AccessionAdditionConfig](
    config_cls=AccessionAdditionConfig,
    check_model_assumptions=check_model_assumptions,
    transform_model=transform_model,
    metadata_transformer_factory=AccessionAdditionMetadataTransformer,
)
