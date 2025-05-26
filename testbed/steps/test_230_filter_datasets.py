# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Step definitions for filtering metadata in the frontend"""

from .conftest import JointFixture, Response, parse, scenarios, then, when
from .utils import search_dataset

scenarios("../features/230_filter_datasets.feature")


@when("I query documents with invalid class name", target_fixture="response")
def query_with_invalid_class(fixtures: JointFixture):
    return search_dataset(fixtures=fixtures, class_name="InvalidClass")


@when(parse('I filter datasets with alias "{alias}"'), target_fixture="response")
def filter_datasets_with_alias(alias: str, fixtures: JointFixture):
    filters = {"alias": alias}
    return search_dataset(fixtures=fixtures, filters=filters)


@when(
    parse('I filter datasets with the study type "{study_type}"'),
    target_fixture="response",
)
def filter_datasets_by_study_type(study_type: str, fixtures: JointFixture):
    filters = {"study.types": study_type}
    return search_dataset(fixtures=fixtures, filters=filters)


@when(
    parse('I filter datasets containing the diagnosis "{diagnosis}"'),
    target_fixture="response",
)
def filter_datasets_by_diagnosis(diagnosis: str, fixtures: JointFixture):
    filters = {"individuals.diagnosis_terms": diagnosis}
    return search_dataset(fixtures=fixtures, filters=filters)


@when(
    parse('I filter datasets using the platform "{platform}"'),
    target_fixture="response",
)
def filter_datasets_by_platform(platform: str, fixtures: JointFixture):
    filters = {"experiment_methods.instrument_model": platform}
    return search_dataset(fixtures=fixtures, filters=filters)


@when(
    parse('I filter datasets with "{file_format}" research data format'),
    target_fixture="response",
)
def filter_dataset_with_file_format(fixtures: JointFixture, file_format):
    filters = {"research_data_files.format": file_format}
    return search_dataset(fixtures=fixtures, filters=filters)


@when(
    "I filter datasets with individual supporting file alias", target_fixture="response"
)
def filter_dataset_for_individual_supporting_file(fixtures: JointFixture):
    filters = {"individual_supporting_files.alias": "INDV_SF_1"}
    return search_dataset(fixtures=fixtures, filters=filters)
