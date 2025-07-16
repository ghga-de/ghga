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

"""Step definitions for downloading files with the GHGA connector"""

import os
import subprocess

from .conftest import (
    Config,
    ConnectorFixture,
    JointFixture,
    given,
    parse,
    scenarios,
    then,
    when,
)
from .utils import verify_named_file

scenarios("../features/340_download_files.feature")


@given("the download buckets are empty")
def download_buckets_empty(fixtures: JointFixture):
    for storage_name in ["primary", "secondary"]:
        storage_config = fixtures.s3.get_storage_config(storage_name)
        fixtures.s3.empty_buckets(
            storages=storage_config,
            buckets=[storage_config.buckets.inbox, storage_config.buckets.staging],
        )


@when(
    parse(
        'I run the GHGA connector download command for "{file_scope}" files in dataset "{dataset_char}"'
    )
)
def run_the_download_command(
    fixtures: JointFixture, file_scope: str, dataset_char: str
):
    download_token = fixtures.state.get_state(
        f"download token for {file_scope} files in dataset {dataset_char}"
    )
    assert download_token and isinstance(download_token, str)
    connector = fixtures.connector
    completed_download = subprocess.run(  # nosec B607, B603
        [
            "ghga-connector",
            "download",
            "--output-dir",
            str(connector.config.download_dir),
            "--debug",
        ],
        cwd=connector.config.work_dir,
        input=download_token,
        capture_output=True,
        check=False,
        encoding="utf-8",
        text=True,
        timeout=180,
    )

    print("Output:")
    print(completed_download.stdout)
    if completed_download.stderr:
        print("Error:")
        print(completed_download.stderr)

    assert "Please paste the complete download token" in completed_download.stdout
    assert "Downloading file" in completed_download.stdout
    assert "ERROR" not in completed_download.stderr


@then(
    parse('"{file_scope}" files in dataset "{dataset_char}" have been downloaded'),
    target_fixture="downloaded_files",
)
def files_are_downloaded(fixtures: JointFixture, file_scope: str, dataset_char: str):
    files = fixtures.state.get_state(
        f"{file_scope} files in dataset {dataset_char} to be downloaded"
    )
    dataset_aliases = fixtures.state.get_state("datasets to be downloaded")
    datasets = fixtures.state.get_state("all available datasets")

    # get all file accessions that belong to the dataset
    assert f"DS_{dataset_char}" in dataset_aliases
    dataset = datasets[f"DS_{dataset_char}"]
    assert "details" in dataset
    details = dataset["details"]
    dataset_file_accessions = set(
        value["accession"]
        for key in details
        if key.endswith("_files")
        for value in details[key]
    )

    download_dir = fixtures.connector.config.download_dir

    file_count = sum(1 for item in os.listdir(download_dir) if not os.path.isdir(item))
    assert len(files) == file_count

    for file_ in files:
        file_id = file_["id"]
        file_extension = file_["extension"]

        assert file_id.startswith("GHGAF")
        assert file_id in dataset_file_accessions

        verify_named_file(
            target_dir=download_dir,
            extension=file_extension,
            name=file_id,
            alias=None,
            encrypted=True,
        )

    return files


@when("I run the decrypt command of the GHGA connector")
def run_the_decrypt_command(fixtures: JointFixture):
    connector = fixtures.connector
    completed_download = subprocess.run(  # nosec B607, B603
        [
            "ghga-connector",
            "decrypt",
            "--input-dir",
            str(connector.config.download_dir),
            "--debug",
        ],
        cwd=connector.config.work_dir,
        capture_output=True,
        check=False,
        encoding="utf-8",
        text=True,
        timeout=60,
    )

    if "Successfully" not in completed_download.stdout:
        print(completed_download.stdout)
    if completed_download.stderr:
        print(completed_download.stderr)

    assert "Successfully decrypted file" in completed_download.stdout
    assert not completed_download.stderr
    assert not completed_download.returncode


@then(
    parse(
        'all downloaded files in dataset "{dataset_char}" have been properly decrypted'
    )
)
def files_have_been_decrypted(
    fixtures: JointFixture, downloaded_files: list[dict[str, str]], dataset_char: str
):
    datasets = fixtures.state.get_state("all available datasets")
    dataset_aliases = fixtures.state.get_state("datasets to be downloaded")

    # get all file aliases that belong to the dataset
    assert f"DS_{dataset_char}" in dataset_aliases
    dataset = datasets[f"DS_{dataset_char}"]
    assert "details" in dataset
    details = dataset["details"]
    dataset_file_aliases = {
        value["accession"]: value["alias"]
        for key in details
        if key.endswith("_files")
        for value in details[key]
    }

    for file_ in downloaded_files:
        file_id = file_["id"]
        file_extension = file_["extension"]

        file_alias = dataset_file_aliases[file_id]

        verify_named_file(
            target_dir=fixtures.connector.config.download_dir,
            extension=file_extension,
            name=file_id,
            alias=file_alias,
            encrypted=False,
        )
