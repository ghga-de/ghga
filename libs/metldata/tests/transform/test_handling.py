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

"""Test the handling module. Only edge cases that are not covered by tests
with builtin transformations are tested here."""

import pytest

from metldata.builtin_transformations.infer_references.main import (
    ReferenceInferenceConfig,
    reference_inference_transformation,
)
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import (
    MetadataModelAssumptionError,
    MetadataModelTransformationError,
    TransformationDefinition,
)
from metldata.transform.handling import TransformationHandler
from tests.fixtures.metadata_models import ADVANCED_VALID_METADATA_MODEL

VALID_EXAMPLE_CONFIG = ReferenceInferenceConfig(
    inferred_ref_map={
        "Experiment": {
            "has_file": {
                "path": "Experiment(has_sample)>Sample(has_file)>File",
                "multivalued": True,
            }
        }
    }
)


def test_transformation_handler_assumption_error():
    """Test using the TransformationHandling when model assumptions are not met."""

    # make transformation definition always raise an MetadataModelAssumptionError:
    def always_failing_assumptions(
        model: MetadataModel, config: ReferenceInferenceConfig
    ):
        """A function that always raises a MetadataModelAssumptionError."""
        raise MetadataModelAssumptionError

    transformation = TransformationDefinition(
        config=reference_inference_transformation.config,
        check_model_assumptions=always_failing_assumptions,
        transform_model=reference_inference_transformation.transform_model,
        metadata_transformer_factory=reference_inference_transformation.metadata_transformer_factory,
    )

    with pytest.raises(MetadataModelAssumptionError):
        _ = TransformationHandler(
            transformation_definition=transformation,
            transformation_config=VALID_EXAMPLE_CONFIG,
            original_model=ADVANCED_VALID_METADATA_MODEL,
        )


def test_transformation_handler_model_transformation_error():
    """Test using the TransformationHandling when model transformation fails."""

    # make transformation definition always raise an MetadataModelAssumptionError:
    def always_failing_transformation(
        original_model: MetadataModel, config: ReferenceInferenceConfig
    ):
        """A function that always raises a MetadataModelTransformationError."""
        raise MetadataModelTransformationError

    transformation = TransformationDefinition(
        config=reference_inference_transformation.config,
        check_model_assumptions=reference_inference_transformation.check_model_assumptions,
        transform_model=always_failing_transformation,
        metadata_transformer_factory=reference_inference_transformation.metadata_transformer_factory,
    )

    with pytest.raises(MetadataModelTransformationError):
        _ = TransformationHandler(
            transformation_definition=transformation,
            transformation_config=VALID_EXAMPLE_CONFIG,
            original_model=ADVANCED_VALID_METADATA_MODEL,
        )
