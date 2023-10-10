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

"""Step definitions for submitting metadata with the datasteward-kit"""

import glob
import os
import subprocess
from pathlib import Path

from .conftest import JointFixture, given, parse, scenarios, then, when

scenarios("../features/10_submit_metadata.feature")


def call_data_steward_kit_submit(
    metadata_path: Path,
    metadata_config_path: Path,
    submission_title: str = "Test Submission",
    submission_description: str = "Test Submission Description",
    timeout: int = 600,
):
    """Call cli command 'ghga-datasteward-kit metadata submit'
    to submit metadata
    """
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
        encoding="utf-8",
        text=True,
        timeout=timeout,
    )

    assert not completed_submit.stdout
    assert "ERROR" not in completed_submit.stderr


@given(parse('we have a valid "{name}" research metadata JSON files'))
def metadata_json_exist(name: str, fixtures: JointFixture):
    metadata_json_path = fixtures.dsk.config.metadata_dir / f"{name}_metadata.json"
    assert metadata_json_path.exists()


@given("we have a valid metadata config YAML file")
def metadata_config_exist(fixtures: JointFixture):
    assert fixtures.dsk.config.metadata_config_path.exists()


@when(parse('"{name}" metadata is submitted to the submission store'))
def submit_metadata(name: str, fixtures: JointFixture):
    workdir = fixtures.dsk.config.submission_registry
    metadata_json_path = fixtures.dsk.config.metadata_dir / f"{name}_metadata.json"
    cwd = os.getcwd()
    os.chdir(workdir)
    call_data_steward_kit_submit(
        metadata_path=metadata_json_path,
        metadata_config_path=fixtures.dsk.config.metadata_config_path,
    )
    os.chdir(cwd)


@then(parse("{num} submission JSON file exists in the local submission store"))
@then(parse("{num} submission JSON files exist in the local submission store"))
def submission_registry_exists(num: str, fixtures: JointFixture):
    try:
        num_expected = {"no": 0, "one": 1, "two": 2}[num]
    except KeyError:
        num_expected = int(num)
    submission_store = fixtures.dsk.config.submission_store
    assert submission_store.exists()

    json_files = glob.glob(os.path.join(submission_store, "*.json"))
    num_found = len(json_files)
    assert (
        num_found == num_expected
    ), f"{num_found} submission JSON files found in '{submission_store}'"
