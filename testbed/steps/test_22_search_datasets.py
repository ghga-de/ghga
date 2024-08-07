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
from .utils import search_dataset

scenarios("../features/22_search_datasets.feature")


@when("I search documents with an unknown class name", target_fixture="response")
def search_with_invalid_query(fixtures: JointFixture):
    return search_dataset(fixtures=fixtures, class_name="Invalid")


@when(
    parse("I search datasets without any keyword"),
    target_fixture="response",
)
def search_items_without_keyword(fixtures: JointFixture):
    return search_dataset(fixtures=fixtures, sorts={"alias": "ascending"})


@then("I get all the existing datasets")
def check_search_without_keyword_results(state: StateStorage, response: Response):
    results = response.json()
    hits = results["hits"]
    assert isinstance(hits, list)
    datasets = {}  # mapping from alias to search summary
    for i, hit in enumerate(hits):
        accession = hit.pop("id_")
        assert accession.startswith("GHGAD")
        hit = hit.pop("content")
        hits[i] = hit
        summary = hit.copy()
        summary["accession"] = accession
        alias = summary.pop("alias")
        datasets[alias] = summary
    # TODO: sorting options should be done in mass and removed here
    for facet in results["facets"]:
        facet["options"].sort(key=lambda x: x["value"])
    assert results == {
        "facets": [
            {
                "key": "study.title",
                "name": "Study",
                "options": [
                    {"value": "The A Study", "count": 1},
                    {"value": "The B Study", "count": 1},
                ],
            },
            {
                "key": "study.types",
                "name": "Study type",
                "options": [
                    {"value": "SYNTHETIC_GENOMICS", "count": 1},
                    {"value": "WHOLE_GENOME_SEQUENCING", "count": 2},
                ],
            },
        ],
        "count": 2,
        "hits": [
            {"alias": "DS_A", "title": "The complete-A dataset"},
            {"alias": "DS_B", "title": "The complete-B dataset"},
        ],
    }
    # memorize the overview of all datasets as mapping from alias to search summary
    state.set_state("all available datasets", datasets)


@when(
    parse('I search datasets with the "{keyword}" query'),
    target_fixture="response",
)
def search_dataset_with_keyword(fixtures: JointFixture, keyword: str):
    return search_dataset(fixtures=fixtures, query=keyword)


@then(parse('I get only dataset "{alias}" as search result'))
def check_study_search_result(alias: str, response: Response):
    results = response.json()
    assert results["count"] == 1
    assert results["hits"][0]["content"]["alias"] == alias


@then("I get the expected results from description search")
def check_description_search_result(response: Response):
    results = response.json()
    assert results["count"] == 1
    hits = results["hits"]
    assert (
        hits[0]["content"]["description"]
        == "An interesting dataset B of complete example set"
    )
