# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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


"""Test the model generation"""

from pytest import raises

from metldata.builtin_transformations.aggregate.model_transform import (
    build_aggregation_model,
)
from metldata.transform.base import MetadataModelTransformationError


def test_valid_config(model_resolved_public, config):
    """Basic test for the construction of a valid output model."""
    model = build_aggregation_model(model=model_resolved_public, config=config)
    for cls_name in ("DatasetStats",):
        assert cls_name in model.schema_view.all_classes()
    for cls_name in ("Study", "Dataset", "Sample"):
        assert cls_name not in model.schema_view.all_classes()


def test_invalid_config(empty_model, invalid_config):
    """Test whether an invalid config with conflicting output paths raises an
    exception.
    """
    with raises(MetadataModelTransformationError):
        build_aggregation_model(model=empty_model, config=invalid_config)
