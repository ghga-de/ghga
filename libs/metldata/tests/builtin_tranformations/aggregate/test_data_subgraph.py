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

"""Test the data aggregation and subgraph"""

from metldata.builtin_transformations.aggregate.cached_model import CachedMetadataModel
from metldata.builtin_transformations.aggregate.data_subgraph import DataSubgraph


def test_data_subgraph_sample_name(
    model_resolved_public, data_complete_1_resolved_public
):
    """The aggregate test"""
    data_branch = DataSubgraph(
        model=CachedMetadataModel(model=model_resolved_public),
        submission_data=data_complete_1_resolved_public,
        origin="SequencingProtocol",
        path_strings=[
            "sequencing_experiments.sequencing_processes.sample.name",
        ],
        visit_once_classes=["Sample"],
    )
    dataset = data_complete_1_resolved_public["sequencing_protocols"][0]
    results = set(data_branch.terminal_nodes(data=dataset))

    assert results == {"GHGAS_tissue_sample1", "GHGAS_blood_sample1"}
