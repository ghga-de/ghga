# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test the governance the loader resolves for every loaded file."""

import json
from collections.abc import Callable
from copy import deepcopy

import pytest

from metldata.artifacts_rest.artifact_info import load_artifact_info
from metldata.governance import (
    FileGovernance,
    GovernanceMetadata,
    resolve_files_governance,
)
from metldata.load.file_governance import resolve_governance_records
from metldata.load.load import ArtifactResourcesInvalid
from metldata.load.models import ArtifactJson, ArtifactResourceDict
from metldata.model_utils.essentials import ALIAS_SLOT, MetadataModel
from metldata.submission_registry.models import Submission
from tests.fixtures.load.joint import (
    ADDED_ACCESSIONS_MODEL_PATH,
    ADDED_ACCESSIONS_PATH,
)
from tests.fixtures.load.utils import copy_as_other_study
from tests.fixtures.utils import BASE_DIR

GOVERNANCE_ARTIFACT_NAME = "added_accessions"
# The submission from which the GHGA archive workflow produces the added_accessions
# artifact the loader tests send:
SUBMISSION_PATH = BASE_DIR / "governance" / "submission.json"
STUDY_CLASS_NAME = "Study"

ARTIFACT_INFO = load_artifact_info(
    name=GOVERNANCE_ARTIFACT_NAME,
    description=GOVERNANCE_ARTIFACT_NAME,
    model=MetadataModel.init_from_path(ADDED_ACCESSIONS_MODEL_PATH),
)
# The submission model anchors the same classes under the same root slots, but
# identifies them by alias instead of by accession.
SUBMISSION_ANCHOR_POINTS = {
    class_name: resource_class.anchor_point.model_copy(
        update={"identifier_slot": ALIAS_SLOT}
    )
    for class_name, resource_class in ARTIFACT_INFO.resource_classes.items()
}


def load_artifact() -> ArtifactJson:
    """Load the added_accessions artifact as the loader receives it."""
    content = json.loads(ADDED_ACCESSIONS_PATH.read_text())["payload"]["content"]
    return ArtifactJson(
        artifact_name=GOVERNANCE_ARTIFACT_NAME,
        study_accession=content["studies"][0]["accession"],
        content=content,
    )


def resolve_at_load(artifacts: list[ArtifactJson]):
    """Resolve the governance records as the loader does."""
    return resolve_governance_records(
        artifact_resources={GOVERNANCE_ARTIFACT_NAME: artifacts},
        artifact_info_dict={GOVERNANCE_ARTIFACT_NAME: ARTIFACT_INFO},
        governance_artifact_name=GOVERNANCE_ARTIFACT_NAME,
    )


def test_same_governance_offline_and_at_load():
    """Test that the loader stores, for every file of an artifact, the governance
    that the offline traversal resolves from the submission the artifact was
    produced from.
    """
    submission = Submission.model_validate_json(SUBMISSION_PATH.read_text())
    submitted_file_accessions = {
        accession
        for root_slot, accessions_by_alias in submission.accession_map.items()
        if root_slot.endswith("_files")
        for accession in accessions_by_alias.values()
    }

    records = resolve_at_load([load_artifact()])
    offline_governance = resolve_files_governance(
        file_accessions=submitted_file_accessions,
        metadata=GovernanceMetadata.from_submissions(
            submissions=[submission],
            anchor_points_by_target=SUBMISSION_ANCHOR_POINTS,
            study_class_name=STUDY_CLASS_NAME,
        ),
    )

    assert {record.file_accession for record in records} == submitted_file_accessions
    for record in records:
        assert offline_governance[record.file_accession] == [
            FileGovernance(**record.model_dump(exclude={"file_accession"}))
        ]


def test_records_of_several_studies():
    """Test that each study's files resolve to that study's governance."""
    first_study = load_artifact()
    second_study = copy_as_other_study(first_study, prefix="SECOND_")

    records = resolve_at_load([first_study, second_study])

    first_records = resolve_at_load([first_study])
    second_records = resolve_at_load([second_study])
    assert records == first_records + second_records
    for record in second_records:
        assert record.file_accession.startswith("SECOND_")
        assert record.dataset_accession
        assert record.dataset_accession.startswith("SECOND_")


def test_no_governance_artifact():
    """Test that a load without the governance artifact resolves no records, even
    though no artifact info is known for it.
    """
    artifact_resources: ArtifactResourceDict = {"stats_public": []}

    assert (
        resolve_governance_records(
            artifact_resources=artifact_resources,
            artifact_info_dict={},
            governance_artifact_name=GOVERNANCE_ARTIFACT_NAME,
        )
        == []
    )


def _dangle_data_access_policies(artifacts: list[ArtifactJson]) -> None:
    """Point every dataset to a data access policy that does not exist."""
    for dataset in artifacts[0]["content"]["datasets"]:
        dataset["data_access_policy"] = "DANGLING"


def _drop_file_accession(artifacts: list[ArtifactJson]) -> None:
    """Remove the accession of the first research data file."""
    del artifacts[0]["content"]["research_data_files"][0]["accession"]


def _share_file_accession_across_studies(artifacts: list[ArtifactJson]) -> None:
    """Add a second study whose first file has the accession of a first-study file."""
    first_study = artifacts[0]
    second_study = copy_as_other_study(first_study, prefix="SECOND_")
    second_study["content"]["research_data_files"][0]["accession"] = first_study[
        "content"
    ]["research_data_files"][0]["accession"]
    artifacts.append(second_study)


def _reuse_file_of_other_dataset(artifacts: list[ArtifactJson]) -> None:
    """Make a file reuse a file of another dataset in the same study, so the reused
    accession matches files in two datasets.
    """
    content = artifacts[0]["content"]
    reused_file = content["research_data_files"][0]
    reusing_file = next(
        file
        for root_slot, resources in content.items()
        if root_slot.endswith("_files")
        for file in resources
        if file["dataset"] != reused_file["dataset"]
    )
    reusing_file["reused_accession"] = reused_file["accession"]


@pytest.mark.parametrize(
    "break_artifacts, expected_message",
    [
        (_dangle_data_access_policies, "DANGLING"),
        (_drop_file_accession, "'accession' is not present"),
        (_share_file_accession_across_studies, "occurs in more than one artifact"),
        (_reuse_file_of_other_dataset, "resolves to 2 datasets"),
    ],
)
def test_invalid_governance_rejected(
    break_artifacts: Callable[[list[ArtifactJson]], None], expected_message: str
):
    """Test that artifacts whose governance cannot be stored unambiguously are
    rejected.
    """
    artifacts = [deepcopy(load_artifact())]
    break_artifacts(artifacts)

    with pytest.raises(ArtifactResourcesInvalid, match=expected_message):
        resolve_at_load(artifacts)
