# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Step definitions for uploading files"""

from .conftest import (
    Config,
    JointFixture,
    MongoFixture,
    Response,
    StateStorage,
    given,
    parse,
    scenarios,
    then,
    when,
)

scenarios("../features/202_upload_completed.feature")


def _rs_study_accessions(fixtures: JointFixture, study_accession: str) -> set[str]:
    """Returns the file accessions RS recognizes for a study."""
    session = fixtures.auth.get_saved_session(
        name="Data Steward", state_store=fixtures.state
    )
    assert session, "No Data Steward session found to query RS studies"
    url = f"{fixtures.config.rs_url}/studies/{study_accession}/file-ids"
    response = fixtures.http.get(url, headers=fixtures.auth.headers(session=session))
    assert response.status_code == 200, (
        f"RS has no study '{study_accession}': {response.status_code} {response.text}"
    )
    return set(response.json())


@when(
    parse(
        'files in "{storage_name}" storage from the "{dataset_alias}" dataset mapped to the "{study_alias}"'
    )
)
def create_accession_mapping(
    storage_name: str, study_alias: str, dataset_alias: str, fixtures: JointFixture
):
    """Build a mapping of file accessions to upload IDs for the given dataset.

    RS keeps its own registry of studies and their file accessions (fed from
    the metldata searchable-resources outbox) and rejects any accession it does not
    already know for the study.
    """
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    box_version = rdub["version"]
    assert box_version, f'Version is missing in "rdub_{storage_name}" state'

    dataset_accessions = fixtures.state.get_state("dataset_accessions")
    assert dataset_alias in dataset_accessions, (
        f"Dataset alias '{dataset_alias}' not found in dataset_accessions state"
    )
    dataset_accession = dataset_accessions[dataset_alias]["dataset_accession"]
    study_accession = dataset_accessions[dataset_alias]["study_accession"]

    rdub_files = fixtures.state.get_state(f"rdub_{storage_name}_files")
    assert rdub_files, f"No rdub_{storage_name}_files found in state"
    alias_to_upload_id = {f["alias"]: f["id"] for f in rdub_files}

    url = (
        f"{fixtures.config.metldata_url}/artifacts/"
        f"embedded_public/classes/EmbeddedDataset/resources/{dataset_accession}"
    )
    response = fixtures.http.get(url)
    assert response.status_code == 200, f"Failed to fetch metadata: {response.text}"
    metadata = response.json()
    assert metadata["study"]["alias"] == study_alias, (
        f"Expected study alias '{study_alias}', got '{metadata['study']['alias']}'"
    )
    alias_to_accession = {
        file_info["alias"]: file_info["accession"]
        for file_field in fixtures.dsk.config.metadata_file_fields
        for file_info in metadata.get(file_field, [])
    }
    mapping = {
        alias_to_accession[alias]: upload_id
        for alias, upload_id in alias_to_upload_id.items()
        if alias in alias_to_accession
    }
    assert mapping, "No uploaded file could be matched to a metadata accession"

    known = _rs_study_accessions(fixtures, study_accession)
    missing = set(mapping) - known
    assert not missing, (
        f"RS does not recognise {len(missing)} accession(s) for study "
        f"{study_accession}: {sorted(missing)}"
    )

    accession_mapping = {
        "box_version": box_version,
        "study_id": study_accession,
        "mapping": mapping,
    }
    fixtures.state.set_state(f"accession_mapping_{study_alias}", accession_mapping)


@when(
    parse(
        '"{full_name}" submits the mapping for "{study_alias}" files in "{storage_name}" storage'
    ),
    target_fixture="response",
)
def submit_mapping(
    full_name: str, study_alias: str, storage_name: str, fixtures: JointFixture
) -> Response:
    """Submit the accession mapping for the given study."""
    accession_mapping = fixtures.state.get_state(f"accession_mapping_{study_alias}")
    assert accession_mapping, f"No accession mapping found for study '{study_alias}'"
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    assert session.user_id, f"user_id is missing for {full_name}"

    accession_mapping = fixtures.state.get_state(f"accession_mapping_{study_alias}")
    assert accession_mapping, f"No accession mapping found for study '{study_alias}'"

    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    assert rdub, f"No RDUB found in state for storage '{storage_name}'"

    rdub_id = rdub["id"]
    url = f"{fixtures.config.rs_url}/upload-boxes/{rdub_id}/file-ids"
    headers = fixtures.auth.headers(session=session)
    return fixtures.http.post(url, json=accession_mapping, headers=headers)


@when(
    parse('"{full_name}" archives the data upload box for "{storage_name}" storage'),
    target_fixture="response",
)
def lock_upload_box(full_name: str, storage_name: str, fixtures: JointFixture):
    """Lock the data upload box for the specified storage scope."""
    assert storage_name in ["primary", "secondary"], f"Unknown storage: {storage_name}"
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    rdub_id = rdub["id"]
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    assert session.user_id, f"user_id is missing for {full_name}"

    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    assert "version" in rdub, f"version is missing in rdub state for {storage_name}"
    data = {"version": rdub["version"], "state": "archived"}
    url = f"{fixtures.config.rs_url}/upload-boxes/{rdub_id}"
    headers = fixtures.auth.headers(session=session)
    return fixtures.http.patch(url, headers=headers, json=data)
