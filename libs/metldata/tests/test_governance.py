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

"""Test the governance traversal."""

import json
from dataclasses import dataclass

import pytest

from metldata.artifacts_rest.models import ArtifactInfo
from metldata.custom_types import Json
from metldata.governance import (
    GovernanceMetadata,
    GovernanceResolutionError,
    resolve_file_governance,
    resolve_files_governance,
)
from metldata.model_utils.anchors import AnchorPoint
from metldata.model_utils.essentials import ALIAS_SLOT
from metldata.submission_registry.models import AccessionMap, Submission
from tests.fixtures.utils import BASE_DIR

ADDED_ACCESSIONS_PATH = BASE_DIR / "load" / "example_metadata" / "added_accessions.json"
ARTIFACT_INFOS_PATH = BASE_DIR / "load" / "example_models" / "artifact_infos.json"
# The submission and the resolved_restricted artifact the GHGA archive workflow
# produces from it with the test bed's model. The workflow also reproduces
# added_accessions from this submission.
SUBMISSION_PATH = BASE_DIR / "governance" / "submission.json"
RESOLVED_RESTRICTED_PATH = BASE_DIR / "governance" / "resolved_restricted.json"
UNKNOWN_FILE_ACCESSION = "GHGAF00000000000000"


def _load_artifact_anchor_points() -> dict[str, AnchorPoint]:
    """Load the anchor points of the resolved_restricted artifact, as the loader
    gets them from its ArtifactInfo.
    """
    [artifact_info] = [
        ArtifactInfo.model_validate(artifact_info)
        for artifact_info in json.loads(ARTIFACT_INFOS_PATH.read_text())
        if artifact_info["name"] == "resolved_restricted"
    ]
    return {
        class_name: resource_class.anchor_point
        for class_name, resource_class in artifact_info.resource_classes.items()
    }


ARTIFACT_ANCHOR_POINTS = _load_artifact_anchor_points()
# The submission model anchors the same classes under the same root slots, but
# identifies them by alias instead of by accession.
SUBMISSION_ANCHOR_POINTS = {
    class_name: anchor_point.model_copy(update={"identifier_slot": ALIAS_SLOT})
    for class_name, anchor_point in ARTIFACT_ANCHOR_POINTS.items()
}


@dataclass
class Study:
    """One study as both an artifact content and the matching submission."""

    content: Json
    accession_map: AccessionMap

    @property
    def submission(self) -> Submission:
        """The submission for the artifact, with aliases as references and no
        accessions.
        """
        alias_by_accession = {
            accession: alias
            for aliases in self.accession_map.values()
            for alias, accession in aliases.items()
        }
        submission_content = {
            root_slot: [
                {
                    slot: _map_strings(value, mapping=alias_by_accession)
                    for slot, value in resource.items()
                    if slot != "accession"
                }
                for resource in resources
            ]
            for root_slot, resources in self.content.items()
        }
        return Submission(
            id=str(id(self)),
            title="test",
            content=submission_content,
            accession_map=self.accession_map,
        )

    @property
    def first_file(self) -> Json:
        """The first research data file."""
        return self.content["research_data_files"][0]


def _map_strings(value, *, mapping: dict[str, str]):
    if isinstance(value, str):
        return mapping.get(value, value)
    if isinstance(value, list):
        return [_map_strings(item, mapping=mapping) for item in value]
    return value


def load_study() -> Study:
    """Load the added_accessions artifact as study A."""
    payload = json.loads(ADDED_ACCESSIONS_PATH.read_text())["payload"]
    return Study(
        content=payload["content"],
        accession_map=payload["annotation"]["accession_map"],
    )


def derive_study(*, base: Study, prefix: str, reused_file: Json | None) -> Study:
    """Copy a study with new accessions. Its first file reuses `reused_file`, if
    given, and the dataset of that file uses the policy DAP_2.
    """
    new_accession_by_accession = {
        accession: f"{prefix}{accession}"
        for aliases in base.accession_map.values()
        for accession in aliases.values()
    }
    content = {
        root_slot: [
            {
                slot: _map_strings(value, mapping=new_accession_by_accession)
                for slot, value in resource.items()
            }
            for resource in resources
        ]
        for root_slot, resources in base.content.items()
    }
    accession_map = {
        root_slot: {
            alias: new_accession_by_accession[accession]
            for alias, accession in aliases.items()
        }
        for root_slot, aliases in base.accession_map.items()
    }
    data_access_policy_2 = accession_map["data_access_policies"]["DAP_2"]
    first_file = content["research_data_files"][0]
    if reused_file is not None:
        first_file["reused_accession"] = reused_file["accession"]
    for dataset in content["datasets"]:
        if dataset["accession"] == first_file["dataset"]:
            dataset["data_access_policy"] = data_access_policy_2
    return Study(content=content, accession_map=accession_map)


def both_representations(studies: list[Study]) -> list[GovernanceMetadata]:
    """Index the same studies once as artifacts and once as submissions."""
    return [
        GovernanceMetadata.from_artifacts(
            contents=[study.content for study in studies],
            anchor_points_by_target=ARTIFACT_ANCHOR_POINTS,
        ),
        GovernanceMetadata.from_submissions(
            submissions=[study.submission for study in studies],
            anchor_points_by_target=SUBMISSION_ANCHOR_POINTS,
        ),
    ]


def test_same_answer_for_submission_and_its_artifact():
    """Test that a submission and the artifact produced from it resolve the same
    governance for every file.
    """
    content = json.loads(RESOLVED_RESTRICTED_PATH.read_text())["payload"]["content"]
    submission = Submission.model_validate_json(SUBMISSION_PATH.read_text())
    file_accessions = [
        file["accession"]
        for class_name, anchor_point in ARTIFACT_ANCHOR_POINTS.items()
        if class_name.endswith("File")
        for file in content[anchor_point.root_slot]
    ]
    assert file_accessions

    from_artifact = resolve_files_governance(
        file_accessions=file_accessions,
        metadata=GovernanceMetadata.from_artifacts(
            contents=[content], anchor_points_by_target=ARTIFACT_ANCHOR_POINTS
        ),
    )
    from_submission = resolve_files_governance(
        file_accessions=file_accessions,
        metadata=GovernanceMetadata.from_submissions(
            submissions=[submission], anchor_points_by_target=SUBMISSION_ANCHOR_POINTS
        ),
    )

    assert from_artifact == from_submission
    for governance in from_artifact.values():
        assert len(governance) == 1


def test_reuse_chain_followed():
    """Test that with follow_reuse_chain a query matches every file in the reuse
    chain and no other file, with equal results for artifacts and submissions.
    B reuses A's file, C reuses B's, and D reuses nothing.
    """
    study_a = load_study()
    study_b = derive_study(base=study_a, prefix="B", reused_file=study_a.first_file)
    study_c = derive_study(base=study_a, prefix="C", reused_file=study_b.first_file)
    study_d = derive_study(base=study_a, prefix="D", reused_file=None)
    all_studies = [study_a, study_b, study_c, study_d]
    cases = [
        ([study_a, study_b], study_b, [study_a, study_b]),
        (all_studies, study_a, [study_a, study_b, study_c]),
        (all_studies, study_c, [study_a, study_b, study_c]),
        (all_studies, study_d, [study_d]),
    ]

    for studies, queried_study, expected_studies in cases:
        from_artifacts, from_submissions = (
            resolve_file_governance(
                file_accession=queried_study.first_file["accession"],
                metadata=metadata,
                follow_reuse_chain=True,
            )
            for metadata in both_representations(studies)
        )
        assert from_artifacts == from_submissions
        assert [governance.dataset_accession for governance in from_artifacts] == [
            study.first_file["dataset"] for study in expected_studies
        ]


def test_loader_pattern_ignores_other_studies():
    """Test that metadata from one artifact alone resolves only that artifact's
    governance, even for a file that reuses another study's file.
    """
    study_a = load_study()
    study_b = derive_study(base=study_a, prefix="B", reused_file=study_a.first_file)

    governance = resolve_file_governance(
        file_accession=study_b.first_file["accession"],
        metadata=GovernanceMetadata.from_artifacts(
            contents=[study_b.content], anchor_points_by_target=ARTIFACT_ANCHOR_POINTS
        ),
    )

    assert [entry.dataset_accession for entry in governance] == [
        study_b.first_file["dataset"]
    ]


def test_submission_without_accessions():
    """Test that files of a submission without accessions resolve with None
    accessions.
    """
    study_a = load_study()
    study_b = derive_study(base=study_a, prefix="B", reused_file=study_a.first_file)
    new_submission = study_b.submission.model_copy(update={"accession_map": {}})

    governance = resolve_file_governance(
        file_accession=study_a.first_file["accession"],
        metadata=GovernanceMetadata.from_submissions(
            submissions=[study_a.submission, new_submission],
            anchor_points_by_target=SUBMISSION_ANCHOR_POINTS,
        ),
    )

    assert len(governance) == 2
    assert governance[1].dataset_accession is None
    assert governance[1].data_access_committee_accession is None
    assert governance[1].data_access_committee_alias == "DAC_1"
    assert governance[1].data_access_policy["name"] == "DAP 2"


def test_unknown_file_accession():
    """Test that an accession that occurs in no file resolves to no governance."""
    for metadata in both_representations([load_study()]):
        assert (
            resolve_file_governance(
                file_accession=UNKNOWN_FILE_ACCESSION, metadata=metadata
            )
            == []
        )


@pytest.mark.parametrize(
    "root_slot, slot_name",
    [
        ("research_data_files", "dataset"),
        ("datasets", "data_access_policy"),
        ("data_access_policies", "data_access_committee"),
    ],
)
def test_dangling_reference(root_slot: str, slot_name: str):
    """Test that a dangling reference anywhere on the chain raises an error."""
    study = load_study()
    for resource in study.content[root_slot]:
        resource[slot_name] = "DANGLING"

    for metadata in both_representations([study]):
        with pytest.raises(GovernanceResolutionError, match="DANGLING"):
            resolve_file_governance(
                file_accession=study.first_file["accession"], metadata=metadata
            )


def test_resource_without_reference():
    """Test that a resource without the slot that holds its reference raises a
    GovernanceResolutionError.
    """
    study = load_study()
    del study.content["datasets"][0]["data_access_policy"]
    del study.content["datasets"][1]["data_access_policy"]

    with pytest.raises(GovernanceResolutionError, match="data_access_policy"):
        resolve_file_governance(
            file_accession=study.first_file["accession"],
            metadata=GovernanceMetadata.from_artifacts(
                contents=[study.content], anchor_points_by_target=ARTIFACT_ANCHOR_POINTS
            ),
        )


def test_same_dataset_in_several_documents():
    """Test that a dataset in several documents yields one entry."""
    study = load_study()

    for metadata in both_representations([study, study]):
        governance = resolve_file_governance(
            file_accession=study.first_file["accession"], metadata=metadata
        )
        assert len(governance) == 1


def test_compared_by_content_only():
    """Test that policies and committees with equal content compare equal even when
    their accession, alias and ega_accession differ, and unequal when content
    differs.
    """
    study_a = load_study()
    study_b = derive_study(base=study_a, prefix="B", reused_file=study_a.first_file)
    data_access_policy_b = next(
        policy
        for policy in study_b.content["data_access_policies"]
        if policy["alias"] == "DAP_1"
    )
    for dataset in study_b.content["datasets"]:
        dataset["data_access_policy"] = data_access_policy_b["accession"]
    for resource in (
        data_access_policy_b,
        *study_b.content["data_access_committees"],
    ):
        resource["alias"] = f"{resource['alias']}_B"
        resource["ega_accession"] = f"{resource.get('ega_accession')}_B"

    governance_a, governance_b = resolve_file_governance(
        file_accession=study_a.first_file["accession"],
        metadata=GovernanceMetadata.from_artifacts(
            contents=[study_a.content, study_b.content],
            anchor_points_by_target=ARTIFACT_ANCHOR_POINTS,
        ),
    )

    assert governance_a.data_access_policy == governance_b.data_access_policy
    assert governance_a.data_access_committee == governance_b.data_access_committee

    study_b.content["data_access_committees"][0]["institute"] = "institute_b"
    governance_a, governance_b = resolve_file_governance(
        file_accession=study_a.first_file["accession"],
        metadata=GovernanceMetadata.from_artifacts(
            contents=[study_a.content, study_b.content],
            anchor_points_by_target=ARTIFACT_ANCHOR_POINTS,
        ),
    )

    assert governance_a.data_access_policy == governance_b.data_access_policy
    assert governance_a.data_access_committee != governance_b.data_access_committee


def test_resolved_restricted_artifact():
    """Test that the traversal works on the resolved_restricted artifact the loader
    receives, whose datasets also hold the references inferred from the files.
    """
    content = json.loads(RESOLVED_RESTRICTED_PATH.read_text())["payload"]["content"]
    metadata = GovernanceMetadata.from_artifacts(
        contents=[content], anchor_points_by_target=ARTIFACT_ANCHOR_POINTS
    )

    [governance] = resolve_file_governance(
        file_accession="GHGAF58002773408921", metadata=metadata
    )

    assert governance.dataset_accession == "GHGAD23572188878277"
    assert governance.data_access_policy_accession == "GHGAP32793167771402"
    assert governance.data_access_policy["name"] == "DAP 1"
    assert governance.data_access_committee_accession == "GHGAC05045906188918"
    assert governance.data_access_committee_alias == "DAC_1"
    assert governance.data_access_committee == {
        "email": "dac_institute_a@dac.dac",
        "institute": "institute_a",
    }

    file_accessions = [
        file["accession"]
        for root_slot in (
            "research_data_files",
            "process_data_files",
            "analysis_method_supporting_files",
            "experiment_method_supporting_files",
            "individual_supporting_files",
        )
        for file in content[root_slot]
    ]
    assert file_accessions
    for governance_list in resolve_files_governance(
        file_accessions=file_accessions, metadata=metadata
    ).values():
        assert len(governance_list) == 1


def test_root_slots_from_anchor_points():
    """Test that a model anchoring a class on the governance chain under another
    root slot resolves the same governance.
    """
    study = load_study()
    expected_governance = resolve_file_governance(
        file_accession=study.first_file["accession"],
        metadata=GovernanceMetadata.from_artifacts(
            contents=[study.content], anchor_points_by_target=ARTIFACT_ANCHOR_POINTS
        ),
    )
    study.content["access_policies"] = study.content.pop("data_access_policies")
    anchor_points_by_target = {
        **ARTIFACT_ANCHOR_POINTS,
        "DataAccessPolicy": ARTIFACT_ANCHOR_POINTS["DataAccessPolicy"].model_copy(
            update={"root_slot": "access_policies"}
        ),
    }

    governance = resolve_file_governance(
        file_accession=study.first_file["accession"],
        metadata=GovernanceMetadata.from_artifacts(
            contents=[study.content], anchor_points_by_target=anchor_points_by_target
        ),
    )

    assert governance == expected_governance
