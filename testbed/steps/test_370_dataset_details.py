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

"""Step definitions for the dataset detail view in the frontend"""

import re

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
from .utils import get_alias_from_ega_accession, get_dataset_search_summary

scenarios("../features/370_dataset_details.feature")


def get_dataset_details(
    ega_accession: str, config: Config, http: HttpClient, state: StateStorage
) -> Response:
    datasets = state.get_state("all available datasets")
    if ega_accession == "non-existing":
        accession = ega_accession
    else:
        alias = get_alias_from_ega_accession(state, ega_accession)
        datasets = state.get_state("all available datasets")
        assert alias in datasets
        accession = datasets[alias]["accession"]
    url = (
        f"{config.metldata_url}/artifacts/"
        f"embedded_public/classes/EmbeddedDataset/resources/{accession}"
    )
    return http.get(url)


@when(
    parse('I request the details of "{ega_accession}" dataset'),
    target_fixture="response",
)
def request_dataset_details(
    ega_accession: str, config: Config, http: HttpClient, state: StateStorage
) -> Response:
    return get_dataset_details(
        ega_accession=ega_accession, config=config, http=http, state=state
    )


@then(parse('I get the details of "{ega_accession}" dataset'))
def check_dataset_details(ega_accession: str, response: Response, state: StateStorage):
    result = response.json()
    assert result
    assert ega_accession == result.get("ega_accession")
    datasets = state.get_state("all available datasets")
    alias = get_alias_from_ega_accession(state, ega_accession)
    assert alias in datasets
    dataset = datasets[alias]
    details = dataset.pop("details", None)
    if details:
        assert result == details
    else:
        summary_result = get_dataset_search_summary(result)
        assert summary_result == dataset
        dataset["details"] = result  # memorize details of the dataset
        datasets = state.set_state("all available datasets", datasets)


@when(
    parse('I request an associated sample resource for "{ega_accession}" dataset'),
    target_fixture="response",
)
def request_one_associated_samples(
    ega_accession: str, config: Config, http: HttpClient, state: StateStorage
) -> Response:
    response = get_dataset_details(
        ega_accession=ega_accession, config=config, http=http, state=state
    )
    result = response.json()
    match = re.search("'sample': '(GHGAN[0-9]+)'", repr(result))
    assert match
    resource_id = match.group(1)
    url = (
        f"{config.metldata_url}/artifacts/"
        f"embedded_public/classes/Sample/resources/{resource_id}"
    )
    return http.get(url)


@then("I get a sample resource")
def check_one_sample_resource(response: Response):
    result = response.json()
    assert isinstance(result, dict)
    assert sorted(result) == [
        "accession",
        "alias",
        "biological_replicate",
        "biospecimen_age_at_sampling",
        "biospecimen_description",
        "biospecimen_isolation",
        "biospecimen_name",
        "biospecimen_storage",
        "biospecimen_tissue_id",
        "biospecimen_tissue_term",
        "biospecimen_type",
        "biospecimen_vital_status_at_sampling",
        "case_control_status",
        "description",
        "disease_or_healthy",
        "ega_accession",
        "experiments",
        "individual",
        "name",
        "storage",
        "type",
    ]
