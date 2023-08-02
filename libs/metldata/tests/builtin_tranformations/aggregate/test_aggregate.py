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


from pprint import pprint

from metldata.builtin_transformations.aggregate.main import AggregateTransformer
from metldata.builtin_transformations.aggregate.model_transform import (
    build_aggregation_model,
)
from metldata.event_handling.models import SubmissionAnnotation


def test_aggregate(ghga_metadata_model, example_data_complete_1, config):
    """Test the aggregate transformation"""
    # Transform the model
    transformed_model = build_aggregation_model(
        model=ghga_metadata_model, config=config
    )

    # Transform the data
    transformer = AggregateTransformer(
        config=config,
        original_model=ghga_metadata_model,
        transformed_model=transformed_model,
    )

    transformed = transformer.transform(
        metadata=example_data_complete_1,
        annotation=SubmissionAnnotation(accession_map={}),
    )

    pprint(transformed)
