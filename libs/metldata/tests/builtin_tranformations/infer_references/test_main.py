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

"""Test the infer_references module."""

import pytest

from metldata.builtin_transformations.infer_references.main import (
    ReferenceInferenceConfig,
    reference_inference_transformation,
)
from metldata.transform.handling import TransformationHandler
from tests.fixtures.metadata_models import ADVANCED_VALID_METADATA_MODEL
from tests.fixtures.transformations import (
    INFERRED_REFERENCE_TEST_CASES,
    TransformationTestCase,
)

ACTIVE_REFERENCE_CONFIG_EXAMPLE = ReferenceInferenceConfig(
    inferred_ref_map={
        "Experiment": {
            "has_file": {
                "path": "Experiment(has_sample)>Sample(has_file)>File",
                "multivalued": True,
            }
        }
    }
)
PASSIVE_REFERENCE_CONFIG_EXAMPLE = ReferenceInferenceConfig(
    inferred_ref_map={
        "File": {
            "has_dataset": {
                "path": "File<(has_file)Dataset",
                "multivalued": True,
            }
        }
    }
)
COMPLEX_REFERENCE_CONFIG_EXAMPLE = ReferenceInferenceConfig(
    inferred_ref_map={
        "Dataset": {
            "has_sample": {
                "path": "Dataset(has_file)>File<(has_file)Sample",
                "multivalued": True,
            }
        }
    }
)


@pytest.mark.parametrize("test_case", INFERRED_REFERENCE_TEST_CASES)
def test_model_transformations(
    test_case: TransformationTestCase[ReferenceInferenceConfig],
):
    """Test the happy path of transforming a model."""

    handler = TransformationHandler(
        transformation_definition=reference_inference_transformation,
        transformation_config=test_case.config,
        original_model=test_case.original_model,
    )
    transformed_model = handler.transformed_model

    assert transformed_model == test_case.transformed_model


@pytest.mark.parametrize("test_case", INFERRED_REFERENCE_TEST_CASES)
def test_metadata_transformations(
    test_case: TransformationTestCase[ReferenceInferenceConfig],
):
    """Test the happy path of transforming a metadata."""

    handler = TransformationHandler(
        transformation_definition=reference_inference_transformation,
        transformation_config=test_case.config,
        original_model=test_case.original_model,
    )
    transformed_metadata = handler.transform_metadata(test_case.original_metadata)

    assert transformed_metadata == test_case.transformed_metadata


def test_model_transformation_passive_happy():
    """Test the happy path of transforming a model with passive inferred reference."""

    handler = TransformationHandler(
        transformation_definition=reference_inference_transformation,
        transformation_config=PASSIVE_REFERENCE_CONFIG_EXAMPLE,
        original_model=ADVANCED_VALID_METADATA_MODEL,
    )
    transformed_model = handler.transformed_model

    # check that the new slot exists:
    transformed_schema_view = transformed_model.schema_view
    new_slot = transformed_schema_view.induced_slot(
        slot_name="has_dataset", class_name="File"
    )
    assert new_slot.range == "Dataset"


def test_model_transformation_complex_happy():
    """Test the happy path of transforming a model with a complex inferred
    reference."""

    handler = TransformationHandler(
        transformation_definition=reference_inference_transformation,
        transformation_config=COMPLEX_REFERENCE_CONFIG_EXAMPLE,
        original_model=ADVANCED_VALID_METADATA_MODEL,
    )
    transformed_model = handler.transformed_model

    # check that the new slot exists:
    transformed_schema_view = transformed_model.schema_view
    new_slot = transformed_schema_view.induced_slot(
        slot_name="has_sample", class_name="Dataset"
    )
    assert new_slot.range == "Sample"
