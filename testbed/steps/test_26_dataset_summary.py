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

"""Step definitions for the dataset summary view in the frontend"""

import httpx

from .conftest import TIMEOUT, Config, StateStorage, parse, scenarios, then, when

scenarios("../features/26_dataset_summary.feature")

EXPECTED_SUMMARIES = {
    "DS_3": {
        "title": "The C dataset",
        "types": ["A Type", "And yet another Type"],
        "dac_email": "dac@dac.dac",
        "description": "An interesting dataset C",
        "samples_summary": {
            "count": 0,
            "stats": {"sex": [], "tissues": [], "phenotypic_features": []},
        },
        "studies_summary": {
            "count": 2,
            "stats": {
                "accessions": 2,
                "titles": "The A Study, The B Study",
            },
        },
        "sequencing_experiments_summary": {
            "count": 0,
            "stats": {"sequencing_protocols": []},
        },
        "files_summary": {
            "count": 20,
            "stats": {"format": [{"value": "FASTQ", "count": 20}], "size": 58720716},
        },
    },
    "DS_A": {
        "title": "The complete-A dataset",
        "types": ["Another Type", "A Type"],
        "dac_email": "dac_institute_a@dac.dac",
        "description": "An interesting dataset A of complete example set",
        "samples_summary": {
            "count": 1,
            "stats": {
                "sex": [{"value": "MALE_SEX_FOR_CLINICAL_USE", "count": 1}],
                "tissues": [{"value": "blood", "count": 1}],
                "phenotypic_features": [{"value": "Leukemia", "count": 1}],
            },
        },
        "studies_summary": {
            "count": 1,
            "stats": {"accessions": 1, "titles": "The A Study"},
        },
        "sequencing_experiments_summary": {
            "count": 1,
            "stats": {
                "sequencing_protocols": [
                    {"value": "ILLUMINA_NOVA_SEQ_6000", "count": 1}
                ]
            },
        },
        "files_summary": {
            "count": 7,
            "stats": {
                "format": [
                    {"value": "FASTQ", "count": 4},
                    {"value": "VCF", "count": 3},
                ],
                "size": 1816,
            },
        },
    },
}


@when(parse('I request the summary of "{alias}" dataset'), target_fixture="response")
def request_dataset_summary(
    alias: str, config: Config, state: StateStorage
) -> httpx.Response:
    datasets = state.get_state("all available datasets")
    if alias == "non-existing":
        resource_id = alias
    else:
        assert alias in datasets
        resource_id = datasets[alias]["accession"]
    url = (
        f"{config.metldata_url}/artifacts/"
        f"stats_public/classes/DatasetStats/resources/{resource_id}"
    )
    return httpx.get(url, timeout=TIMEOUT)


@then(parse('I get the summary of "{alias}" dataset'))
def check_dataset_summary(alias: str, response: httpx.Response):
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
