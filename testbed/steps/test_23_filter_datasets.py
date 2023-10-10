# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from .conftest import Config, JointFixture, Response, parse, scenarios, then, when
from .utils import search_dataset_rpc

scenarios("../features/23_filter_datasets.feature")


@when("I query documents with invalid class name", target_fixture="response")
def query_with_invalid_class(fixtures: JointFixture):
    return search_dataset_rpc(fixtures=fixtures, class_name="InvalidClass")


@when("I filter dataset with alias", target_fixture="response")
def filter_dataset_with_alias(fixtures: JointFixture):
    filters = [{"key": "alias", "value": "DS_A"}]
    return search_dataset_rpc(fixtures=fixtures, filters=filters)


@then("I get the expected results from alias filter")
def check_alias_filter(response: Response):
    results = response.json()
    assert results["count"] == 1
    hits = results["hits"]
    assert hits[0]["content"]["alias"] == "DS_A"


@when(
    parse('I filter dataset with "{file_format}" study file format'),
    target_fixture="response",
)
def filter_dataset_with_file_format(fixtures: JointFixture, file_format):
    filters = [{"key": "study_files.format", "value": file_format}]
    return search_dataset_rpc(fixtures=fixtures, filters=filters)


@when("I filter dataset with sequencing file alias", target_fixture="response")
def filter_dataset_for_sequencing_process_file(fixtures: JointFixture):
    filters = [{"key": "sequencing_process_files.alias", "value": "SEQ_FILE_6"}]
    return search_dataset_rpc(fixtures=fixtures, filters=filters)


@then("I get the expected results from sequencing file filter")
def check_sequencing_file_filter(response: Response):
    results = response.json()
    assert results["count"] == 1
    hits = results["hits"]
    assert hits[0]["content"]["alias"] == "DS_B"
