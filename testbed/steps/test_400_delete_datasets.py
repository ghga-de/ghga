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

"""Step definitions for deleting datasets"""

import subprocess
from pathlib import Path

from .conftest import (
    Config,
    JointFixture,
    MongoFixture,
    Response,
    parse,
    scenarios,
    then,
    when,
)
from .test_130_load_metadata import run_the_load_command
from .utils import get_dataset_overview, search_dataset

scenarios("../features/400_delete_datasets.feature")


def is_dataset_a_and_b(event_file: Path) -> bool:
    """Check whether the given event file is a submission for a complete dataset."""
    event = open(event_file).read()
    return (
        '"type_": "source_event"' in event
        and '"submission_id":' in event
        and '"title": "The complete' in event
    )


@when("the artifacts for the complete datasets are removed from the event store")
def delete_artifacts_for_complete_datasets(fixtures: JointFixture):
    event_path = fixtures.dsk.config.event_store
    source_event = None
    for event_file in (event_path / "source_events").glob("*.json"):
        if is_dataset_a_and_b(event_file):
            assert not source_event
            source_event = event_file.name
    assert source_event
    num_artifact_types = num_deleted_artifacts = 0
    for artifact_dir in event_path.glob("artifact*"):
        if not artifact_dir.is_dir():
            continue
        num_artifact_types += 1
        artifact_path = artifact_dir / source_event
        if artifact_path.exists():
            artifact_path.unlink()
            num_deleted_artifacts += 1
    assert num_artifact_types == 6
    if num_deleted_artifacts:  # allow that they have already been deleted
        assert num_deleted_artifacts == num_artifact_types


# The following step is re-used from the artifact loading test
when("metadata is loaded into the system")(run_the_load_command)


@then("dataset stats in the database are empty")
def check_dataset_stats_in_metldata_database(config: Config, mongo: MongoFixture):
    dataset_stats = mongo.wait_for_documents(
        config.metldata_db_name, "art_stats_public_class_DatasetStats", {}, timeout=5
    )
    assert not dataset_stats


@then("no datasets exist as embedded datasets in the database")
def check_embedded_datasets_in_metldata_database(config: Config, mongo: MongoFixture):
    embedded_datasets = mongo.wait_for_documents(
        config.metldata_db_name,
        "art_embedded_public_class_EmbeddedDataset",
        {},
        timeout=5,
    )
    assert not embedded_datasets


@then("searching for datasets without keyword returns no datasets")
def searching_yields_only_minimal_datasets(fixtures: JointFixture):
    response = search_dataset(fixtures=fixtures)
    results = response.json()
    assert results["count"] == 0


@then("no datasets are known to the work package service")
def check_datasets_in_wps_database(config: Config, mongo: MongoFixture):
    datasets = mongo.wait_for_documents(config.wps_db_name, "datasets", {}, timeout=5)
    assert not datasets


@then("no access grants exist any more in the claims repository")
def check_access_grants_in_claims_repository(config: Config, mongo: MongoFixture):
    grants = mongo.wait_for_documents(
        config.ums_db_name,
        config.ums_claims_collection,
        {"visa_type": "ControlledAccessGrants"},
    )
    assert not grants


@when(parse('"{full_name}" lists the datasets'), target_fixture="response")
def query_datasets_with_wps(fixtures: JointFixture, full_name: str):
    # This step is the copy of the one in the work package creation test
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session
    user_id = session.user_id
    url = f"{fixtures.config.wps_url}/users/{user_id}/datasets"
    headers = fixtures.auth.headers(session=session)
    return fixtures.http.get(url, headers=headers)


@then("no dataset is returned")
def check_no_datasets_in_list(response: Response):
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@when(
    "I run the GHGA connector download command for all files",
    target_fixture="download_attempt",
)
def run_the_download_command(fixtures: JointFixture) -> subprocess.CompletedProcess:
    download_token = fixtures.state.get_state(
        "download token for all files in dataset A"
    )
    assert download_token and isinstance(download_token, str)
    connector = fixtures.connector
    download_attempt = subprocess.run(  # nosec B607, B603
        [
            "ghga-connector",
            "download",
            "--output-dir",
            str(connector.config.download_dir),
        ],
        cwd=connector.config.work_dir,
        input=download_token,
        capture_output=True,
        check=False,
        encoding="utf-8",
        text=True,
        timeout=10,  # short timeout since we don't actually want to download anything
    )

    print("Output:")
    print(download_attempt.stdout)
    print("Error:")
    print(download_attempt.stderr)

    return download_attempt


@then("I get an error message that the token is not valid")
def check_failed_attempt(download_attempt: subprocess.CompletedProcess):
    assert "Please paste the complete download token" in download_attempt.stdout
    assert "auth token is not valid" in download_attempt.stderr
    assert download_attempt.returncode == 1
