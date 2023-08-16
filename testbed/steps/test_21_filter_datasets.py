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

import httpx

from .conftest import Config, parse, scenarios, then, when
from .utils import search_dataset_rpc

scenarios("../features/21_filter_datasets.feature")


@when("I query documents with invalid class name", target_fixture="response")
def query_with_invalid_class(config: Config):
    return search_dataset_rpc(config, class_name="InvalidClass")


@when("I filter dataset with alias", target_fixture="response")
def filter_dataset_with_alias(config: Config):
    filters = [{"key": "alias", "value": "DS_A"}]
    return search_dataset_rpc(config, filters)


@then("I get the expected results from alias filter")
def check_alias_filter(response: httpx.Response):
    results = response.json()
    assert results["count"] == 1
    hits = results["hits"]
    assert hits[0]["content"]["alias"] == "DS_A"


@when(
    parse('I filter dataset with "{file_format}" study file format'),
    target_fixture="response",
)
def filter_dataset_with_file_format(config: Config, file_format):
    filters = [{"key": "study_files.format", "value": file_format}]
    return search_dataset_rpc(config, filters)


@when("I filter dataset with sequencing file alias", target_fixture="response")
def filter_dataset_for_sequencing_process_file(config: Config):
    filters = [{"key": "sequencing_process_files.alias", "value": "SEQ_FILE_6"}]
    return search_dataset_rpc(config, filters)


@then("I get the expected results from sequencing file filter")
def check_sequencing_file_filter(response: httpx.Response):
    results = response.json()
    assert results["count"] == 1
    hits = results["hits"]
    assert hits[0]["content"]["alias"] == "DS_B"
