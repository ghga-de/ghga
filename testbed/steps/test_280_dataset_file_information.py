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

"""Step definitions for the dataset file information"""

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

scenarios("../features/280_dataset_file_information.feature")

EXPECTED_DATASET_FILE_COUNT = {
    "DS_A": 7,
    "DS_B": 7,
}


def get_all_dataset_information(
    alias: str, config: Config, http: HttpClient, state: StateStorage
) -> Response:
    """Get the information for all files in the given dataset"""
    datasets = state.get_state("all available datasets")
    if alias == "non-existing":
        dataset_accession = alias
    else:
        assert alias in datasets
        dataset_accession = datasets[alias]["accession"]
    url = f"{config.dins_url}/dataset_information/{dataset_accession}"
    return http.get(url)


def get_file_information_from_metadata(file_metadata):
    """Extract the file information from the metadata"""
    return {
        "size": file_metadata["Unencrypted file size"],
        "sha256_hash": file_metadata["Unencrypted file checksum"],
        "storage_alias": file_metadata["Storage alias"],
    }


@when(
    parse('I request the details of all files in "{alias}" dataset'),
    target_fixture="response",
)
def request_dataset_file_information(
    alias: str, config: Config, http: HttpClient, state: StateStorage
) -> Response:
    return get_all_dataset_information(
        alias=alias, config=config, http=http, state=state
    )


@then(parse('I get the details of all files in "{alias}" dataset'))
def check_dataset_file_information(alias: str, response: Response, state: StateStorage):
    result = response.json()
    assert result
    datasets = state.get_state("all available datasets")
    assert datasets[alias]["accession"] == result.get("accession")
    dataset_file_information = result["file_information"]
    assert len(dataset_file_information) == EXPECTED_DATASET_FILE_COUNT[alias]
    all_file_information = state.get_state("all file information")
    for file in dataset_file_information:
        accession = file.pop("accession")
        file_metadata = all_file_information[accession]
        file_information = get_file_information_from_metadata(file_metadata)
        assert file_information == file


@when(
    parse('I request the details of "{file_reference}" file'), target_fixture="response"
)
def request_single_file_information(
    file_reference: str, config: Config, http: HttpClient, state: StateStorage
) -> Response:
    all_file_information = state.get_state("all file information")
    file_id = (
        min(all_file_information)
        if file_reference == "single"
        else "non-existing"
        if file_reference == "non-existing"
        else ValueError(f"Unknown file reference: {file_reference}")
    )
    url = f"{config.dins_url}/file_information/{file_id}"
    return http.get(url)


@then("I get the details of the file correctly")
def check_single_file_information(response: Response, state: StateStorage):
    result = response.json()
    assert result
    all_file_information = state.get_state("all file information")
    accession = result.pop("accession")
    file_metadata = all_file_information[accession]
    file_information = get_file_information_from_metadata(file_metadata)
    assert file_information == result
