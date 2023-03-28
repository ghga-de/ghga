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

"""Logic for handling Transformation."""

from metldata.custom_types import Json
from metldata.model_utils.essentials import MetadataModel
from metldata.model_utils.metadata_validator import MetadataValidator
from metldata.transform.base import Config, TransformationDefinition


class TransformationHandler:
    """Used for executing transformations described in a TransformationDefinition."""

    def __init__(
        self,
        transformation_definition: TransformationDefinition[Config],
        transformation_config: Config,
        original_model: MetadataModel,
    ):
        """Initialize the TransformationHandler by checking the assumptions made on the
        original model and transforming the model as described in the transformation
        definition. The transformed model is available at the `transformed_model`
        attribute.

        Raises:
            ModelAssumptionError:
                if the assumptions made on the original model are not met.
        """

        self._definition = transformation_definition
        self._config = transformation_config
        self._original_model = original_model

        self._definition.check_model_assumptions(self._original_model, self._config)
        self.transformed_model = self._definition.transform_model(
            self._original_model, self._config
        )
        self._metadata_transformer = self._definition.metadata_transformer_factory(
            config=self._config,
            original_model=self._original_model,
            transformed_model=self.transformed_model,
        )

        self._original_metadata_validator = MetadataValidator(
            model=self._original_model
        )
        self._transformed_metadata_validator = MetadataValidator(
            model=self.transformed_model
        )

    def transform_metadata(self, metadata: Json) -> Json:
        """Transforms metadata using the transformation definition. Validates the
        original metadata against the original model and the transformed metadata
        against the transformed model.

        Raises:
            MetadataTransformationError:
                if the transformation fails.
        """

        self._original_metadata_validator.validate(metadata)
        transformed_metadata = self._metadata_transformer.transform(metadata=metadata)
        self._transformed_metadata_validator.validate(transformed_metadata)

        return transformed_metadata
