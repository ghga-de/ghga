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
    async_step,
    given,
    parse,
    scenarios,
    then,
    when,
)
from .utils import verify_named_file

scenarios("../features/34_download_files.feature")


@given("the download buckets are empty")
@async_step
async def download_buckets_empty(fixtures: JointFixture):
    config = fixtures.config
    await fixtures.s3.empty_buckets(
        buckets=[config.inbox_bucket, config.staging_bucket]
    )


@given("I have an empty working directory for the GHGA connector")
def clean_connector_work_dir(connector: ConnectorFixture):
    connector.reset_work_dir()


@given("my Crypt4GH key pair has been stored in two key files")
def keys_are_made_available(connector: ConnectorFixture, config: Config):
    connector.store_keys(
        public_key=config.user_public_crypt4gh_key,
        private_key=config.user_private_crypt4gh_key,
    )


@when(parse('I run the GHGA connector download command for "{file_scope}" files'))
def run_the_download_command(fixtures: JointFixture, file_scope: str):
    download_token = fixtures.state.get_state(f"download token for {file_scope} files")
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
    assert not completed_download.stderr


@then(
    parse('"{file_scope}" files announced in metadata have been downloaded'),
    target_fixture="downloaded_files",
)
def files_are_downloaded(fixtures: JointFixture, file_scope: str):
    files = fixtures.state.get_state(f"{file_scope} files to be downloaded")
    dataset_alias = fixtures.state.get_state("dataset to be downloaded")
    datasets = fixtures.state.get_state("all available datasets")

    # get all file accessions that belong to the dataset
    assert dataset_alias in datasets
    dataset = datasets[dataset_alias]
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


@then("all downloaded files have been properly decrypted")
def files_have_been_decrypted(
    fixtures: JointFixture, downloaded_files: list[dict[str, str]]
):
    datasets = fixtures.state.get_state("all available datasets")
    dataset_alias = fixtures.state.get_state("dataset to be downloaded")

    # get all file aliases that belong to the dataset
    assert dataset_alias in datasets
    dataset = datasets[dataset_alias]
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
