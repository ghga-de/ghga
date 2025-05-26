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

"""Step definitions for the dataset summary view in the frontend"""

from .conftest import (
    Config,
    HttpClient,
    Response,
    StateStorage,
    parse,
    scenarios,
    then,
    when,
)

scenarios("../features/260_dataset_summary.feature")

EXPECTED_SUMMARIES = {
    "DS_B": {
        "title": "The complete-B dataset",
        "dac_email": "dac_institute_a@dac.dac",
        "types": ["And another Type"],
        "description": "An interesting dataset B of complete example set",
        "samples_summary": {
            "count": 2,
            "stats": {
                "sex": [{"value": "MALE", "count": 1}],
                "tissues": [
                    {"value": "blood", "count": 1},
                    {"value": "subcutaneous adipose tissue", "count": 1},
                ],
                "phenotypic_features": [{"value": "Leukemia", "count": 1}],
            },
        },
        "studies_summary": {
            "count": 1,
            "stats": {"accessions": 1, "titles": "The B Study"},
        },
        "experiments_summary": {
            "count": 2,
            "stats": {"experiment_methods": [{"value": "454_GS", "count": 2}]},
        },
        "files_summary": {
            "count": 7,
            "stats": {
                "format": [{"value": "FASTQ", "count": 6}, {"value": "TXT", "count": 1}]
            },
        },
    },
    "DS_A": {
        "title": "The complete-A dataset",
        "dac_email": "dac_institute_a@dac.dac",
        "types": ["Another Type", "A Type"],
        "description": "An interesting dataset A of complete example set",
        "samples_summary": {
            "count": 2,
            "stats": {
                "sex": [{"value": "MALE", "count": 1}],
                "tissues": [
                    {"value": "blood", "count": 1},
                    {"value": "subcutaneous adipose tissue", "count": 1},
                ],
                "phenotypic_features": [{"value": "Leukemia", "count": 1}],
            },
        },
        "studies_summary": {
            "count": 1,
            "stats": {"accessions": 1, "titles": "The A Study"},
        },
        "experiments_summary": {
            "count": 2,
            "stats": {"experiment_methods": [{"value": "454_GS", "count": 3}]},
        },
        "files_summary": {
            "count": 7,
            "stats": {
                "format": [
                    {"value": "FASTQ", "count": 3},
                    {"value": "JSON", "count": 1},
                    {"value": "TXT", "count": 1},
                    {"value": "VCF", "count": 2},
                ]
            },
        },
    },
}


@when(parse('I request the summary of "{alias}" dataset'), target_fixture="response")
def request_dataset_summary(
    alias: str, config: Config, http: HttpClient, state: StateStorage
) -> Response:
    datasets = state.get_state("all available datasets")
    if alias == "non-existing":
        accession = alias
    else:
        assert alias in datasets
        accession = datasets[alias]["accession"]
    url = (
        f"{config.metldata_url}/artifacts/"
        f"stats_public/classes/DatasetStats/resources/{accession}"
    )
    return http.get(url)


@then(parse('I get the summary of "{alias}" dataset'))
def check_dataset_summary(alias: str, response: Response):
    result = response.json()
    accession = result.pop("accession")
    assert accession.startswith("GHGAD")
    studies_summary = result["studies_summary"]["stats"]
    accessions = studies_summary.pop("accession")
    assert all(accession.startswith("GHGAS") for accession in accessions)
    studies_summary["accessions"] = len(accessions)
    studies_summary["titles"] = ", ".join(sorted(studies_summary.pop("title")))
    assert alias in EXPECTED_SUMMARIES
    assert result == EXPECTED_SUMMARIES[alias]
