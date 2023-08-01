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

# pylint: disable=redefined-outer-name

from pathlib import Path

import yaml
from pytest import fixture, raises

from metldata.builtin_transformations.aggregate.config import AggregateConfig
from metldata.builtin_transformations.aggregate.model_transform import (
    build_aggregation_model,
)
from metldata.custom_types import Json
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import MetadataModelTransformationError
from tests.fixtures.metadata import _get_example_metadata
from tests.fixtures.metadata_models import _get_example_model
from tests.fixtures.utils import BASE_DIR


def load_yaml(path: Path) -> Json:
    """Loads yaml or json file from the specified sub-path of the tests/fixtures
    directory and returns the contents as a dictionary."""
    with open(BASE_DIR.joinpath(path), encoding="utf8") as in_stream:
        return yaml.safe_load(in_stream)


@fixture
def empty_model() -> MetadataModel:
    """An empty LinkML MetadataModel"""
    return MetadataModel(id="test", name="test")


@fixture
def model_0_10_0() -> MetadataModel:
    """The GHGA submission metadata model version 1.0.0"""
    return _get_example_model("ghga_submission_1.0.0")


@fixture
def example_data_complete_1() -> Json:
    """Official GHGA example data "complete_1" version 1.0.0+1"""
    return _get_example_metadata("ghga_example_minimal_1_0.10.0+1")


@fixture
def config() -> AggregateConfig:
    """A working config"""
    return AggregateConfig.parse_obj(
        load_yaml(Path("transformations/aggregate/config.yaml"))
    )


@fixture
def invalid_config() -> AggregateConfig:
    """An invalid config with conflicting output paths."""
    return AggregateConfig.parse_obj(
        load_yaml(Path("transformations/aggregate/config_invalid.yaml"))
    )


def test_valid_config(model_0_10_0, config):
    """Basic test for the construction of a valid output model."""
    model = build_aggregation_model(model=model_0_10_0, config=config)
    for cls_name in ("Submission", "StudyStats", "DatasetStats", "StringValueCount"):
        assert cls_name in model.schema_view.all_classes()
    for cls_name in ("Study", "Dataset", "Sample"):
        assert cls_name not in model.schema_view.all_classes()


def test_invalid_config(empty_model, invalid_config):
    """Test whether an invalid config with conflicting output paths raises an
    exception."""
    with raises(MetadataModelTransformationError):
        build_aggregation_model(model=empty_model, config=invalid_config)
