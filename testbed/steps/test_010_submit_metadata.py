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

"""Step definitions for submitting metadata with the datasteward-kit"""

import glob
import json
import os
import subprocess
from pathlib import Path

from .conftest import JointFixture, given, parse, scenarios, then, when

scenarios("../features/010_submit_metadata.feature")


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
        check=False,
        encoding="utf-8",
        text=True,
        timeout=timeout,
    )

    if completed_submit.stdout:
        print(completed_submit.stdout)
    if "ERROR" in completed_submit.stderr or completed_submit.returncode:
        print(completed_submit.stderr)

    assert not completed_submit.stdout
    assert "ERROR" not in completed_submit.stderr
    assert not completed_submit.returncode


@given("we have valid research metadata JSON files")
def metadata_json_exist(fixtures: JointFixture):
    for metadata_json_path in fixtures.dsk.config.submission_metadata_paths:
        assert metadata_json_path.exists()


@given("we have a valid metadata config YAML file")
def metadata_config_exist(fixtures: JointFixture):
    assert fixtures.dsk.config.metadata_config_path.exists()


@when("the metadata is submitted to the submission store")
def submit_metadata(fixtures: JointFixture):
    workdir = fixtures.dsk.config.submission_registry
    cwd = os.getcwd()
    os.chdir(workdir)
    submission_store = fixtures.dsk.config.submission_store
    # one submission per study, since a submission holds exactly one study
    for metadata_json_path in fixtures.dsk.config.submission_metadata_paths:
        known_ids = {path.stem for path in submission_store.glob("*.json")}
        call_data_steward_kit_submit(
            metadata_path=metadata_json_path,
            metadata_config_path=fixtures.dsk.config.metadata_config_path,
        )
        # submit does not print the ID, so it is the one file the call added
        [new_id] = {path.stem for path in submission_store.glob("*.json")} - known_ids
        fixtures.state.set_state(f"submission id {metadata_json_path.stem}", new_id)
    os.chdir(cwd)


def call_data_steward_kit_amend(
    submission_id: str,
    metadata_path: Path,
    metadata_config_path: Path,
    timeout: int = 600,
):
    """Call cli command 'ghga-datasteward-kit metadata amend'
    to amend an already accessioned submission
    """
    completed_amend = subprocess.run(  # nosec B607, B603
        [
            "ghga-datasteward-kit",
            "metadata",
            "amend",
            "--submission-id",
            submission_id,
            "--metadata-path",
            metadata_path,
            "--config-path",
            metadata_config_path,
        ],
        capture_output=True,
        check=False,
        encoding="utf-8",
        text=True,
        timeout=timeout,
    )

    if completed_amend.stdout:
        print(completed_amend.stdout)
    if "ERROR" in completed_amend.stderr or completed_amend.returncode:
        print(completed_amend.stderr)

    # unlike submit, amend reports what it changed on stdout
    assert "ERROR" not in completed_amend.stderr
    assert not completed_amend.returncode


def read_submission(fixtures: JointFixture, submission_id: str) -> dict:
    """Read a submission JSON from the local submission store."""
    submission_path = (
        Path(fixtures.dsk.config.submission_store) / f"{submission_id}.json"
    )
    with open(submission_path, encoding="utf-8") as submission_file:
        return json.load(submission_file)


@when(
    "the submission is amended with the same metadata",
    target_fixture="amendment",
)
def amend_metadata(fixtures: JointFixture):
    # the first study's submission stands for all, as amend treats each alike
    metadata_json_path = fixtures.dsk.config.submission_metadata_paths[0]
    submission_id = fixtures.state.get_state(f"submission id {metadata_json_path.stem}")
    accessions_before = read_submission(fixtures, submission_id)["accession_map"]

    workdir = fixtures.dsk.config.submission_registry
    cwd = os.getcwd()
    os.chdir(workdir)
    try:
        call_data_steward_kit_amend(
            submission_id=submission_id,
            metadata_path=metadata_json_path,
            metadata_config_path=fixtures.dsk.config.metadata_config_path,
        )
    finally:
        os.chdir(cwd)

    submission_after = read_submission(fixtures, submission_id)

    return {
        "accessions_before": accessions_before,
        "submission_after": submission_after,
    }


@then("the accessions of the submission are unchanged")
def accessions_unchanged(amendment: dict):
    submission_after = amendment["submission_after"]

    assert submission_after["accession_map"] == amendment["accessions_before"]
    assert submission_after["status_history"][-1]["new_status"] == "completed"


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
    assert num_found == num_expected, (
        f"{num_found} submission JSON files found in '{submission_store}'"
    )
