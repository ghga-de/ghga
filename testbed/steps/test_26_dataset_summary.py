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

from .conftest import (
    TIMEOUT,
    Config,
    MongoFixture,
    get_state,
    parse,
    scenarios,
    then,
    when,
)

scenarios("../features/26_dataset_summary.feature")

EXPECTED_SUMMARIES = {
    "DS_3": {
        "title": "The C dataset",
        "types": ["A Type", "And yet another Type"],
        "dac_email": "dac@dac.dac",
        "sample_summary": {
            "count": 0,
            "stats": {"sex": [], "tissues": [], "phenotypes": []},
        },
        "study_summary": {
            "count": 2,
            "stats": {
                "accessions": 2,
                "title": ["The B Study", "The A Study"],
            },
        },
        "experiment_summary": {"count": 0, "stats": {"protocol": []}},
        "file_summary": {
            "count": 20,
            "stats": {"format": [{"value": "FASTQ", "count": 20}]},
        },
    },
    "DS_A": {
        "title": "The complete-A dataset",
        "types": ["Another Type", "A Type"],
        "dac_email": "dac_institute_a@dac.dac",
        "sample_summary": {
            "count": 1,
            "stats": {
                "sex": [{"value": "MALE_SEX_FOR_CLINICAL_USE", "count": 1}],
                "tissues": [{"value": "blood", "count": 1}],
                "phenotypes": [{"value": "Leukemia", "count": 1}],
            },
        },
        "study_summary": {
            "count": 1,
            "stats": {"accessions": 1, "title": ["The A Study"]},
        },
        "experiment_summary": {
            "count": 1,
            "stats": {"protocol": [{"value": "ILLUMINA_NOVA_SEQ_6000", "count": 1}]},
        },
        "file_summary": {
            "count": 7,
            "stats": {
                "format": [{"value": "FASTQ", "count": 4}, {"value": "VCF", "count": 3}]
            },
        },
    },
}


@when(parse('I request the summary of "{alias}" dataset'), target_fixture="response")
def request_dataset_summary(
    alias: str, config: Config, mongo: MongoFixture
) -> httpx.Response:
    datasets = get_state("all available datasets", mongo)
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
    accessions = result["study_summary"]["stats"].pop("accession")
    assert all(accession.startswith("GHGAS") for accession in accessions)
    result["study_summary"]["stats"]["accessions"] = len(accessions)
    assert alias in EXPECTED_SUMMARIES
    assert result == EXPECTED_SUMMARIES[alias]
