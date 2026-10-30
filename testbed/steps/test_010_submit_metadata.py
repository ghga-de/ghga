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
import shutil
from contextlib import chdir
from pathlib import Path

from .conftest import JointFixture, given, parse, scenarios, then, when
from .utils import is_legacy_accession, read_submission, run_dskit

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
    completed_submit = run_dskit(
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
        timeout=timeout,
    )

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


@given("the submission store holds the legacy submission of study X")
def seed_legacy_submission(fixtures: JointFixture):
    config = fixtures.dsk.config
    shutil.copyfile(config.legacy_accession_store_path, config.accession_store)
    with open(config.legacy_submission_path, encoding="utf-8") as submission_file:
        submission_id = json.load(submission_file)["id"]
    shutil.copyfile(
        config.legacy_submission_path, config.submission_store / f"{submission_id}.json"
    )
    fixtures.state.set_state(
        f"submission id {config.legacy_metadata_path.stem}", submission_id
    )


@when("the accession store is migrated")
def migrate_accession_store(fixtures: JointFixture):
    # the config names the store relative to the submission registry
    with chdir(fixtures.dsk.config.submission_registry):
        completed_migrate = run_dskit(
            "metadata",
            "migrate-accession-store",
            "--config-path",
            fixtures.dsk.config.metadata_config_path,
        )

    assert not completed_migrate.returncode, completed_migrate.stderr


@then("the accession store keeps the flat accessions as legacy ones")
def accession_store_migrated(fixtures: JointFixture):
    config = fixtures.dsk.config
    frozen_store = config.legacy_accession_store_path.read_text(encoding="utf-8")

    with open(config.accession_store, encoding="utf-8") as store_file:
        assert json.load(store_file) == {"legacy": frozen_store.split(), "years": {}}
    backup = config.accession_store.with_name(f"{config.accession_store.name}.bak")
    assert backup.read_text(encoding="utf-8") == frozen_store


@when("the metadata is submitted to the submission store")
def submit_metadata(fixtures: JointFixture):
    submission_store = fixtures.dsk.config.submission_store
    # one submission per study, since a submission holds exactly one study
    for metadata_json_path in fixtures.dsk.config.submission_metadata_paths:
        known_ids = {path.stem for path in submission_store.glob("*.json")}
        with chdir(fixtures.dsk.config.submission_registry):
            call_data_steward_kit_submit(
                metadata_path=metadata_json_path,
                metadata_config_path=fixtures.dsk.config.metadata_config_path,
            )
        # submit does not print the ID, so it is the one file the call added
        [new_id] = {path.stem for path in submission_store.glob("*.json")} - known_ids
        fixtures.state.set_state(f"submission id {metadata_json_path.stem}", new_id)


def amend_submission(
    fixtures: JointFixture, *, submission_id: str, metadata_path: Path
) -> dict:
    """Amend the submission with the metadata, and return its ID, the finished
    process, the accession map before and the submission after the amendment.
    """
    accessions_before = read_submission(fixtures, submission_id)["accession_map"]

    with chdir(fixtures.dsk.config.submission_registry):
        completed_amend = run_dskit(
            "metadata",
            "amend",
            "--submission-id",
            submission_id,
            "--metadata-path",
            metadata_path,
            "--config-path",
            fixtures.dsk.config.metadata_config_path,
        )

    return {
        "submission_id": submission_id,
        "completed_amend": completed_amend,
        "accessions_before": accessions_before,
        "submission_after": read_submission(fixtures, submission_id),
    }


@when(
    "the submission is amended with the same metadata",
    target_fixture="amendment",
)
def amend_metadata(fixtures: JointFixture):
    # the first study's submission stands for all, as submit gives each study PIDs
    metadata_json_path = fixtures.dsk.config.submission_metadata_paths[0]
    submission_id = fixtures.state.get_state(f"submission id {metadata_json_path.stem}")
    return amend_submission(
        fixtures, submission_id=submission_id, metadata_path=metadata_json_path
    )


@when(
    "the legacy submission of study X is amended with an added file",
    target_fixture="amendment",
)
def amend_legacy_submission(fixtures: JointFixture):
    metadata_json_path = fixtures.dsk.config.legacy_metadata_path
    submission_id = fixtures.state.get_state(f"submission id {metadata_json_path.stem}")
    return amend_submission(
        fixtures, submission_id=submission_id, metadata_path=metadata_json_path
    )


@then("the amendment is refused, since the submission has study PIDs")
def amendment_refused(amendment: dict):
    completed_amend = amendment["completed_amend"]

    assert completed_amend.returncode
    assert "AccessionNotLegacyError" in completed_amend.stderr


@then("the accessions of the submission are unchanged")
def accessions_unchanged(amendment: dict):
    submission_after = amendment["submission_after"]

    assert submission_after["accession_map"] == amendment["accessions_before"]
    assert submission_after["status_history"][-1]["new_status"] == "completed"


@then("the amendment is applied")
def amendment_applied(amendment: dict):
    completed_amend = amendment["completed_amend"]

    assert not completed_amend.returncode, completed_amend.stderr
    assert f"Submission {amendment['submission_id']} amended." in completed_amend.stdout


@then("the legacy submission keeps its accessions")
def legacy_accessions_kept(amendment: dict):
    submission_after = amendment["submission_after"]
    accessions_after = submission_after["accession_map"]

    for root_slot, accessions in amendment["accessions_before"].items():
        for alias, accession in accessions.items():
            assert accessions_after.get(root_slot, {}).get(alias) == accession, alias
    assert submission_after["status_history"][-1]["new_status"] == "completed"


@then("the added file has a flat accession")
def added_file_accessioned(amendment: dict, fixtures: JointFixture):
    accessions_before = amendment["accessions_before"]
    accessions_after = amendment["submission_after"]["accession_map"]
    added = {
        (root_slot, alias): accession
        for root_slot, accessions in accessions_after.items()
        for alias, accession in accessions.items()
        if alias not in accessions_before.get(root_slot, {})
    }

    assert set(added) == {("research_data_files", "RESEARCH_DATA_FILE_X2")}
    content = amendment["submission_after"]["content"]
    assert "RESEARCH_DATA_FILE_X2" in {
        file_["alias"] for file_ in content["research_data_files"]
    }
    [accession] = added.values()
    assert accession.startswith("GHGAF") and is_legacy_accession(accession)
    # the frozen accessions must survive too, or a later amend could mint a used one
    config = fixtures.dsk.config
    frozen = config.legacy_accession_store_path.read_text(encoding="utf-8").split()
    with open(config.accession_store, encoding="utf-8") as store_file:
        legacy = set(json.load(store_file)["legacy"])
    assert {*frozen, accession} <= legacy


@then(parse("{num} submission JSON file exists in the local submission store"))
@then(parse("{num} submission JSON files exist in the local submission store"))
def submission_registry_exists(num: str, fixtures: JointFixture):
    try:
        num_expected = {"no": 0, "one": 1, "two": 2, "three": 3}[num]
    except KeyError:
        num_expected = int(num)
    submission_store = fixtures.dsk.config.submission_store
    assert submission_store.exists()

    json_files = glob.glob(os.path.join(submission_store, "*.json"))
    num_found = len(json_files)
    assert num_found == num_expected, (
        f"{num_found} submission JSON files found in '{submission_store}'"
    )
