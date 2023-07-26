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

import pytest
from pytest import fixture

from metldata.builtin_transformations.aggregate.model_transform import (
    create_aggregate_model,
)
from metldata.model_utils.essentials import MetadataModel


@fixture
def leaf_ranges() -> list[str]:
    return ["string", "integer", "KeyValue", "KeyValue", "integer", "string"]


@fixture
def leaf_multivalued() -> list[bool]:
    return [False, False, True, True, False, False]


@fixture
def invalid_path_strings() -> list[str]:
    """Example input data for the ModelGenerator class."""
    return [
        "id",
        "sample_summary.count",
        "sample_summary.count.tissues",
        "sample_summary.stats.phenotypes",
        "study_summary.count",
        "study_summary.stats.title",
    ]


@fixture
def path_strings() -> list[str]:
    """Example path strings"""
    return [
        "id",
        "sample_summary.count",
        "sample_summary.stats.tissues",
        "sample_summary.stats.phenotypes",
        "study_summary.count",
        "study_summary.stats.title",
    ]


@fixture
def empty_model() -> MetadataModel:
    """An empty LinkML MetadataModel"""
    return MetadataModel(id="test", name="test")


def test_model_generator_invalid(
    empty_model, invalid_path_strings, leaf_ranges, leaf_multivalued
):
    """Test that the model generation raises an error if the provided paths are
    incompatible with eachother."""
    with pytest.raises(RuntimeError):
        create_aggregate_model(
            model=empty_model,
            path_strings=invalid_path_strings,
            leaf_ranges=leaf_ranges,
            leaf_multivalued=leaf_multivalued,
        )


def test_model_generator(empty_model, path_strings, leaf_ranges, leaf_multivalued):
    """Test the happy case for model generation."""
    create_aggregate_model(
        model=empty_model,
        path_strings=path_strings,
        leaf_ranges=leaf_ranges,
        leaf_multivalued=leaf_multivalued,
    )
