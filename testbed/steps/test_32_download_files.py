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

"""Step definitions for file download tests"""

import subprocess

from .conftest import (
    Config,
    ConnectorFixture,
    JointFixture,
    S3Fixture,
    async_step,
    get_state,
    given,
    scenarios,
    then,
    when,
)
from .utils import verify_named_file

scenarios("../features/32_download_files.feature")


@given("the download buckets are empty")
@async_step
async def download_buckets_empty(s3: S3Fixture):
    await s3.empty_given_buckets(["inbox", "staging"])


@given("I have an empty working directory for the GHGA connector")
def clean_connector_work_dir(connector: ConnectorFixture):
    connector.reset_work_dir()


@given("my Crypt4GH key pair has been stored in two key files")
def keys_are_made_available(connector: ConnectorFixture, config: Config):
    connector.store_keys(
        public_key=config.user_public_crypt4gh_key,
        private_key=config.user_private_crypt4gh_key,
    )


@when("I run the download command of the GHGA connector")
def run_the_download_command(fixtures: JointFixture):
    download_token = get_state("a download token has been created", fixtures.mongo)
    assert download_token and isinstance(download_token, str)
    connector = fixtures.connector
    completed_download = subprocess.run(  # nosec B607, B603
        [
            "ghga-connector",
            "download",
            "--output-dir",
            str(connector.config.download_dir),
        ],
        cwd=connector.config.work_dir,
        input=download_token,
        capture_output=True,
        check=True,
        encoding="utf-8",
        text=True,
        timeout=90,
    )

    assert "Please paste the complete download token" in completed_download.stdout
    assert "Downloading file" in completed_download.stdout
    assert not completed_download.stderr


@then("all files announced in metadata have been downloaded")
def files_are_downloaded(fixtures: JointFixture):
    files = get_state("files to be downloaded", fixtures.mongo)

    for file_ in files:
        verify_named_file(
            target_dir=fixtures.connector.config.download_dir,
            extension=file_["extension"],
            name=file_["id"],
            encrypted=True,
        )


@when("I run the decrypt command of the GHGA connector")
def run_the_decrypt_command(fixtures: JointFixture):
    connector = fixtures.connector
    completed_download = subprocess.run(  # nosec B607, B603
        [
            "ghga-connector",
            "decrypt",
            "--input-dir",
            str(connector.config.download_dir),
        ],
        cwd=connector.config.work_dir,
        capture_output=True,
        check=True,
        encoding="utf-8",
        text=True,
        timeout=60,
    )

    assert "Successfully decrypted file" in completed_download.stdout
    assert not completed_download.stderr


@then("all downloaded files have been properly decrypted")
def files_have_been_decrypted(fixtures: JointFixture):
    files = get_state("files to be downloaded", fixtures.mongo)

    for file_ in files:
        verify_named_file(
            target_dir=fixtures.connector.config.download_dir,
            extension=file_["extension"],
            name=file_["id"],
            encrypted=False,
        )
