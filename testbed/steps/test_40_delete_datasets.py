# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
    given,
    parse,
    scenarios,
    then,
    when,
)
from .test_13_load_metadata import run_the_load_command
from .test_32_work_packages import query_datasets_with_wps
from .test_33_download_files import clean_connector_work_dir, keys_are_made_available
from .utils import get_dataset_overview, search_dataset_rpc

scenarios("../features/40_delete_datasets.feature")


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
    assert num_artifact_types == 5
    if num_deleted_artifacts:  # allow that they have already been deleted
        assert num_deleted_artifacts == num_artifact_types


# The following step is re-used from the artifact loading test
when("metadata is loaded into the system")(run_the_load_command)


@then("the stats in the database show only the minimal datasets")
def check_dataset_stats_in_metldata_database(config: Config, mongo: MongoFixture):
    if config.use_api_gateway:
        return  # black-box testing: skip checking the database directly
    dataset_stats = mongo.wait_for_documents(
        config.metldata_db_name, "art_stats_public_class_DatasetStats", {}
    )
    assert dataset_stats
    assert len(dataset_stats) == 4  # only the 4 minimal datasets remain
    dataset_names = {
        dataset.get("content", {})
        .get("title", "?")
        .removeprefix("The ")
        .removesuffix(" dataset")
        for dataset in dataset_stats
    }
    # complete-A and complete-B have been deleted, only the minimal datasets remain
    assert dataset_names == {"A", "B", "C", "D"}


@then("only the minimal datasets exist as embedded datasets in the database")
def check_embedded_datasets_in_metldata_database(config: Config, mongo: MongoFixture):
    if config.use_api_gateway:
        return  # black-box testing: skip checking the database directly
    embedded_datasets = mongo.wait_for_documents(
        config.metldata_db_name, "art_embedded_public_class_EmbeddedDataset", {}
    )
    assert embedded_datasets
    assert len(embedded_datasets) == 4  # only the 4 minimal datasets remain
    dataset_names = {
        dataset.get("content", {})
        .get("title", "?")
        .removeprefix("The ")
        .removesuffix(" dataset")
        for dataset in embedded_datasets
    }
    # complete-A and complete-B have been deleted, only the minimal datasets remain
    assert dataset_names == {"A", "B", "C", "D"}


@then("searching for datasets without keyword finds only the minimal datasets")
def searching_yields_only_minimal_datasets(fixtures: JointFixture):
    response = search_dataset_rpc(fixtures=fixtures)
    results = response.json()
    assert results["count"] == 4
    # get an overview of all datasets
    contents = [hit["content"] for hit in results["hits"]]
    datasets = {content["alias"]: get_dataset_overview(content) for content in contents}
    # check that only the minimal datasets and their files can be found
    num_files = {alias: len(dataset["files"]) for alias, dataset in datasets.items()}
    assert num_files == {"DS_1": 16, "DS_2": 6, "DS_3": 20, "DS_4": 10}


@then("only the minimal datasets are known to the work package service")
def check_datasets_in_wps_database(config: Config, mongo: MongoFixture):
    if config.use_api_gateway:
        return  # black-box testing: skip checking the database directly
    datasets = mongo.wait_for_documents(config.wps_db_name, "datasets", {})
    assert datasets
    assert len(datasets) == 4
    dataset_names = {
        dataset.get("title", "?").removeprefix("The ").removesuffix(" dataset")
        for dataset in datasets
    }
    # complete-A and complete-B have been deleted, only the minimal datasets remain
    assert dataset_names == {"A", "B", "C", "D"}


@then("no access grants exist any more in the claims repository")
def check_access_grants_in_claims_repository(config: Config, mongo: MongoFixture):
    if config.use_api_gateway:
        return  # black-box testing: skip checking the database directly
    grants = mongo.wait_for_documents(
        config.ums_db_name,
        config.ums_claims_collection,
        {"visa_type": "ControlledAccessGrants"},
    )
    assert not grants


# The following step is re-used from the work package creation test
when("the list of datasets is queried", target_fixture="response")(
    query_datasets_with_wps
)


@then("no dataset is returned")
def check_no_datasets_in_list(response: Response):
    data = response.json()
    assert isinstance(data, list) and len(data) == 0


# The following steps are re-used from the file download test
given("I have an empty working directory for the GHGA connector")(
    clean_connector_work_dir
)
given("my Crypt4GH key pair has been stored in two key files")(keys_are_made_available)


@when(
    "I run the GHGA connector download command for all files",
    target_fixture="download_attempt",
)
def run_the_download_command(fixtures: JointFixture) -> subprocess.CompletedProcess:
    download_token = fixtures.state.get_state("download token for all files")
    assert download_token and isinstance(download_token, str)
    connector = fixtures.connector
    return subprocess.run(  # nosec B607, B603
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
        timeout=5,
    )


@then("I get an error message that the token is not valid")
def check_failed_attempt(download_attempt: subprocess.CompletedProcess):
    assert "Please paste the complete download token" in download_attempt.stdout
    assert "auth token is not valid" in download_attempt.stderr
    assert download_attempt.returncode == 1
