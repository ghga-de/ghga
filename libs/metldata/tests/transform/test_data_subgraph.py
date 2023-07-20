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

import yaml
from pytest import fixture

from metldata.builtin_transformations.aggregate.data_subgraph import DataSubgraph
from metldata.custom_types import Json
from metldata.model_utils.essentials import ExportableSchemaView, MetadataModel
from tests.fixtures.utils import BASE_DIR


@fixture
def original_model() -> MetadataModel:
    """The test metadata model"""
    schema_view = ExportableSchemaView(
        str(
            BASE_DIR.joinpath("transformations")
            .joinpath("aggregate")
            .joinpath("original_model.yaml")
        )
    )
    return schema_view.export_model()


@fixture
def original_data() -> Json:
    """The original data"""
    with open(
        BASE_DIR.joinpath("transformations")
        .joinpath("aggregate")
        .joinpath("original_metadata.yaml"),
        encoding="utf8",
    ) as file:
        return yaml.safe_load(file)


def test_data_subgraph_sample_name(original_model, original_data):
    """The aggregate test"""
    data_branch = DataSubgraph(
        model=original_model,
        submission_data=original_data,
        origin="Dataset",
        path_strings=[
            "sample_files.sample.name",
        ],
        visit_once_classes=["Sample"],
    )
    results = set(data_branch.terminal_nodes(original_data["datasets"][0]))
    assert results == {"sample 1", "sample 2"}


def test_data_subgraph_condition_name(original_model, original_data):
    """The aggregate test"""
    data_branch = DataSubgraph(
        model=original_model,
        submission_data=original_data,
        origin="Dataset",
        # Looping back to conditions from samples yields an additional sample
        # which is otherwise disconnected
        path_strings=[
            "sample_files.sample.condition.samples.name",
        ],
    )
    results = set(data_branch.terminal_nodes(original_data["datasets"][0]))
    assert results == {"sample 1", "sample 2", "sample 3"}
