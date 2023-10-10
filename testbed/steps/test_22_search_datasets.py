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

"""Step definitions for searching metadata in the frontend"""

from .conftest import (
    JointFixture,
    Response,
    StateStorage,
    parse,
    scenarios,
    then,
    when,
)
from .utils import get_dataset_overview, search_dataset_rpc

scenarios("../features/22_search_datasets.feature")


@when("I search documents with invalid query format", target_fixture="response")
def search_with_invalid_query(fixtures: JointFixture):
    invalid_query = {"Invalid": "Query"}
    return search_dataset_rpc(fixtures=fixtures, query=invalid_query)  # type: ignore


@when(
    parse("I search datasets without any keyword"),
    target_fixture="response",
)
def search_items_without_keyword(fixtures: JointFixture):
    return search_dataset_rpc(fixtures=fixtures)


@then("I get all the existing datasets")
def check_search_without_keyword_results(state: StateStorage, response: Response):
    results = response.json()
    assert results["count"] == 6
    # get an overview of all datasets
    contents = [hit["content"] for hit in results["hits"]]
    datasets = {content["alias"]: get_dataset_overview(content) for content in contents}
    # check that datasets and their files are complete
    num_files = {alias: len(dataset["files"]) for alias, dataset in datasets.items()}
    assert num_files == {
        "DS_1": 16,
        "DS_2": 6,
        "DS_3": 20,
        "DS_4": 10,
        "DS_A": 7,
        "DS_B": 12,
    }
    # memorize the overview of all datasets
    state.set_state("all available datasets", datasets)


@when(
    parse('I search datasets with the "{keyword}" query'),
    target_fixture="response",
)
def search_dataset(fixtures: JointFixture, keyword: str):
    return search_dataset_rpc(fixtures=fixtures, query=keyword)


@then("I get the expected results from study search")
def check_study_search_result(response: Response):
    results = response.json()
    assert results["count"] == 4
    contents = [hit["content"] for hit in results["hits"]]
    studies = {
        content["alias"]: {study["title"] for study in content["studies"]}
        for content in contents
    }
    assert studies == {
        "DS_1": {"The A Study"},
        "DS_2": {"The A Study"},
        "DS_3": {"The A Study", "The B Study"},
        "DS_A": {"The A Study"},
    }


@then("I get the expected results from description search")
def check_description_search_result(response: Response):
    results = response.json()
    assert results["count"] == 1
    hits = results["hits"]
    assert hits[0]["content"]["description"] == "An interesting dataset C"
