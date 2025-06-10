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

scenarios("../features/220_search_datasets.feature")

SEARCH_ALL_DATASETS = {
    "facets": [
        {
            "key": "study.types",
            "name": "Study type",
            "options": [
                {"value": "SYNTHETIC_GENOMICS", "count": 1},
                {"value": "WHOLE_GENOME_SEQUENCING", "count": 2},
            ],
        },
        {
            "key": "experiment_methods.instrument_model",
            "name": "Platform",
            "options": [{"value": "454_GS", "count": 2}],
        },
        {
            "key": "experiment_methods.type",
            "name": "Experiment",
            "options": [{"value": "DNA-seq", "count": 2}],
        },
        {
            "key": "experiment_methods.library_type",
            "name": "Analysis level",
            "options": [{"value": "WGS", "count": 2}],
        },
        {
            "key": "experiment_methods.sequencing_layout",
            "name": "Sequencing mode",
            "options": [{"value": "SE", "count": 2}],
        },
        {
            "key": "individuals.diagnosis_terms",
            "name": "Diagnosis",
            "options": [{"value": "Myeloid leukaemia", "count": 2}],
        },
        {
            "key": "data_access_policy.alias",
            "name": "Access policy",
            "options": [{"value": "DAP_1", "count": 1}, {"value": "DAP_2", "count": 1}],
        },
        {
            "key": "data_access_policy.data_access_committee.institute",
            "name": "Controller Institution",
            "options": [{"value": "institute_a", "count": 2}],
        },
    ],
    "count": 2,
    "hits": [
        {
            "alias": "DS_A",
            "ega_accession": "EGADATASET12345",
            "title": "The complete-A dataset",
        },
        {
            "alias": "DS_B",
            "ega_accession": "EGADATASET12346",
            "title": "The complete-B dataset",
        },
    ],
}


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
    assert results == SEARCH_ALL_DATASETS
    # memorize the overview of all datasets as mapping from alias to search summary
    state.set_state("all available datasets", datasets)


@when(
    parse('I search datasets with the "{keyword}" query'),
    target_fixture="response",
)
def search_dataset_with_keyword(fixtures: JointFixture, keyword: str):
    return search_dataset(fixtures=fixtures, query=keyword)


@then("I get the expected results from description search")
def check_description_search_result(response: Response):
    results = response.json()
    assert results["count"] == 1
    hits = results["hits"]
    assert (
        hits[0]["content"]["description"]
        == "An interesting dataset B of complete example set"
    )
