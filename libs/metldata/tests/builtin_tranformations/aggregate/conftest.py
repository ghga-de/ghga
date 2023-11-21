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
from pathlib import Path

import yaml
from pytest import fixture
from tests.fixtures.metadata import _get_example_metadata
from tests.fixtures.metadata_models import _get_example_model
from tests.fixtures.utils import BASE_DIR

from metldata.builtin_transformations.aggregate import AggregateConfig
from metldata.custom_types import Json
from metldata.model_utils.essentials import MetadataModel


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
def model_resolved_public() -> MetadataModel:
    """The GHGA submission metadata model version 1.0.0"""
    return _get_example_model("ghga_1.1.0_resolved_public")


@fixture
def data_complete_1_resolved_public() -> Json:
    """Official GHGA example data "complete_1" version 1.0.0+1"""
    return _get_example_metadata("complete_1_1.1.0+1.resolved_public")


@fixture
def config() -> AggregateConfig:
    """A working config"""
    return AggregateConfig.model_validate(
        load_yaml(Path("transformations/aggregate/default/config.yaml"))
    )


@fixture
def invalid_config() -> AggregateConfig:
    """An invalid config with conflicting output paths."""
    return AggregateConfig.model_validate(
        load_yaml(Path("transformations/aggregate/config_invalid.yaml"))
    )
