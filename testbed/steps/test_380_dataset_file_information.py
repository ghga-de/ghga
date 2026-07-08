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

scenarios("../features/380_dataset_file_information.feature")

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
        "accession": file_metadata["accession"],
        "size": file_metadata["decrypted_size"],
        "sha256_hash": file_metadata["decrypted_sha256"],
        "storage_alias": file_metadata["storage_alias"],
    }


@when(
    parse('I request the details of all files in "{alias}" dataset'),
    target_fixture="response",
)
def request_dataset_file_information(
    alias: str, config: Config, http: HttpClient, state: StateStorage
) -> Response:
    """Request the information for all files in the given dataset"""
    return get_all_dataset_information(
        alias=alias, config=config, http=http, state=state
    )


@then(parse('I get the details of all files in "{alias}" dataset'))
def check_dataset_file_information(alias: str, response: Response, state: StateStorage):
    """Check that the file information matches the metadata for all files in the dataset"""
    result = response.json()
    assert result
    rdub = "primary" if alias == "DS_A" else "secondary" if alias == "DS_B" else None
    assert rdub, f"Unknown dataset alias: {alias}"
    files = state.get_state(f"rdub_{rdub}_files")
    files = {file["accession"]: file for file in files}

    dataset_file_information = result["file_information"]
    assert len(dataset_file_information) == EXPECTED_DATASET_FILE_COUNT[alias]

    for file_information in dataset_file_information:
        accession = file_information["accession"]
        assert accession in files, f"Unexpected file accession: {accession}"
        file_metadata = get_file_information_from_metadata(files[accession])
        assert file_information == file_metadata


@when(
    parse('I request the details of "{file_reference}" file'), target_fixture="response"
)
def request_single_file_information(
    file_reference: str, config: Config, http: HttpClient, state: StateStorage
) -> Response:
    """Request the information for a single file"""
    files = state.get_state("rdub_primary_files")
    if file_reference == "single":
        file_id = min(files, key=lambda f: f["accession"])["accession"]
    elif file_reference == "non-existing":
        file_id = "non-existing"
    else:
        raise ValueError(f"Unknown file reference: {file_reference}")
    url = f"{config.dins_url}/file_information/{file_id}"
    return http.get(url)


@then("I get the details of the file correctly")
def check_single_file_information(response: Response, state: StateStorage):
    """Check that the file information matches the metadata for the single file"""
    result = response.json()
    assert result
    files = state.get_state("rdub_primary_files")
    files = {file["accession"]: file for file in files}
    accession = result["accession"]
    file_metadata = files[accession]
    file_information = get_file_information_from_metadata(file_metadata)
    assert file_information == result
