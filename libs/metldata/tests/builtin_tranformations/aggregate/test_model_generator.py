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

from pytest import fixture, raises

from metldata.builtin_transformations.aggregate.config import AggregateConfig
from metldata.builtin_transformations.aggregate.model_transform import (
    build_aggregation_model,
)
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import MetadataModelTransformationError


@fixture
def empty_model() -> MetadataModel:
    """An empty LinkML MetadataModel"""
    return MetadataModel(id="test", name="test")


@fixture
def valid_config():
    aggregations = [
        {
            "input_paths": ["some.input.path"],
            "output_path": "dataset.stats.phenotypes.count",
            "operation": "Count",
        },
        {
            "input_paths": ["some.other.input.path"],
            "output_path": "dataset.stats.phenotypes.counts",
            "operation": "IntegerElementCount",
        },
    ]
    return AggregateConfig.parse_obj({"aggregations": aggregations})


@fixture
def invalid_config():
    aggregations = [
        {
            "input_paths": ["some.input.path"],
            "output_path": "dataset.stats.phenotypes.count",
            "operation": "Count",
        },
        {
            "input_paths": ["some.other.input.path"],
            "output_path": "dataset.stats.phenotypes",
            "operation": "IntegerElementCount",
        },
    ]
    return AggregateConfig.parse_obj({"aggregations": aggregations})


def test_valid_config(empty_model, valid_config):
    build_aggregation_model(model=empty_model, config=valid_config)


def test_invalid_config(empty_model, invalid_config):
    with raises(MetadataModelTransformationError):
        build_aggregation_model(model=empty_model, config=invalid_config)
