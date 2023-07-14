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

""" Step definitions for metadata submission """

import glob
import os
import subprocess  # nosec B404
from pathlib import Path

from .conftest import TIMEOUT, JointFixture, given, scenarios, then, when

scenarios("../features/10_submit_metadata.feature")


def call_data_steward_kit_submit(
    metadata_path: Path,
    metadata_config_path: Path,
    submission_title: str = "Test Submission",
    submission_description: str = "Test Submission Description",
    timeout: int = TIMEOUT,
):
    """Call cli command 'ghga-datasteward-kit metadata submit'
    to submit metadata"""

    completed_submit = subprocess.run(  # nosec B607, B603
        [
            "ghga-datasteward-kit",
            "metadata",
            "submit",
            "--submission-title",
            submission_title,
            "--submission-description",
            submission_description,
            "--metadata-path",
            metadata_path,
            "--config-path",
            metadata_config_path,
        ],
        capture_output=True,
        check=True,
        timeout=timeout * 60,
    )

    assert not completed_submit.stdout
    assert b"ERROR" not in completed_submit.stderr


@given("we have a valid research metadata JSON file")
def metadata_json_exist(fixtures: JointFixture):
    assert fixtures.submission.config.metadata_path.exists()


@given("we have a valid metadata config YAML file")
def metadata_config_exist(fixtures: JointFixture):
    assert fixtures.submission.config.metadata_config_path.exists()


@when("metadata is submitted to the submission registry")
def submit_metadata(fixtures: JointFixture):
    workdir = fixtures.submission.config.submission_registry
    cwd = os.getcwd()
    os.chdir(workdir)
    call_data_steward_kit_submit(
        metadata_path=fixtures.submission.config.metadata_path,
        metadata_config_path=fixtures.submission.config.metadata_config_path,
    )
    os.chdir(cwd)


@then("a submission JSON exists in the local submission registry")
def submission_registry_exists(fixtures: JointFixture):
    submission_store = fixtures.submission.config.submission_store
    assert submission_store.exists()

    json_files = glob.glob(os.path.join(submission_store, "*.json"))
    assert json_files, f"No submission JSON files found in '{submission_store}'"
