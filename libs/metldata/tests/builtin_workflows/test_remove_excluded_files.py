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

"""Test that the GHGA archive workflow removes files excluded from the submission."""

import json

import pytest
import yaml

from metldata.builtin_workflows.ghga_archive import GHGA_ARCHIVE_WORKFLOW
from metldata.custom_types import Json
from metldata.event_handling.models import SubmissionAnnotation
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.handling import WorkflowHandler
from tests.fixtures.utils import BASE_DIR, read_yaml

CASE_DIR = BASE_DIR / "workflows" / "ghga_archive_workflow" / "simple"

FILE_CLASSES = ("SampleFile", "ExperimentFile")
INCLUDED_ACCESSIONS = {
    "TESTF0000000001",
    "TESTF0000000002",
    "TESTF0000000003",
    "TESTF0000000004",
}
EXCLUDED_SAMPLE_FILE = ("test_sample_01_R3", "TESTF0000000005")
EXCLUDED_EXPERIMENT_FILE = ("test_sample_02_R3", "TESTF0000000006")
EXCLUDED_ACCESSIONS = {EXCLUDED_SAMPLE_FILE[1], EXCLUDED_EXPERIMENT_FILE[1]}


@pytest.fixture(name="artifacts", scope="module")
def artifacts_fixture(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Json]:
    """Run the workflow on the simple case, extended by one excluded file per file
    class that the dataset references, and return the artifacts.
    """
    model = read_yaml(CASE_DIR / "original_model.yaml")
    model["slots"]["included_in_submission"] = {"range": "boolean"}
    for class_name in FILE_CLASSES:
        model["classes"][class_name]["slots"].append("included_in_submission")
        model["classes"][class_name]["slot_usage"]["included_in_submission"] = {
            "required": True
        }
    model_path = tmp_path_factory.mktemp("model") / "model.yaml"
    model_path.write_text(yaml.safe_dump(model))

    metadata = read_yaml(CASE_DIR / "original_metadata.yaml")
    annotation = read_yaml(CASE_DIR / "metadata_annotation.yaml")
    for root_slot, (alias, accession) in (
        ("sample_files", EXCLUDED_SAMPLE_FILE),
        ("experiment_files", EXCLUDED_EXPERIMENT_FILE),
    ):
        for file in metadata[root_slot]:
            file["included_in_submission"] = True
        metadata[root_slot].append(
            {
                **metadata[root_slot][0],
                "alias": alias,
                "filename": f"{alias}.fastq",
                "included_in_submission": False,
            }
        )
        metadata["datasets"][0][root_slot].append(alias)
        annotation["accession_map"][root_slot][alias] = accession

    config = read_yaml(CASE_DIR / "config.yaml")
    config["remove_excluded_files"] = {
        "resources_to_delete": {
            class_name: {"included_in_submission": False} for class_name in FILE_CLASSES
        }
    }

    handler = WorkflowHandler(
        workflow_definition=GHGA_ARCHIVE_WORKFLOW,
        workflow_config=GHGA_ARCHIVE_WORKFLOW.config_cls(**config),
        original_model=MetadataModel.init_from_path(model_path),
    )
    return handler.run(metadata=metadata, annotation=SubmissionAnnotation(**annotation))


def test_excluded_files_are_kept_before_the_removal(artifacts: dict[str, Json]):
    """The artifact taken before the removal step still declares the excluded files."""
    added_accessions = json.dumps(artifacts["added_accessions"])

    for accession in EXCLUDED_ACCESSIONS | INCLUDED_ACCESSIONS:
        assert accession in added_accessions


@pytest.mark.parametrize(
    "artifact",
    sorted(set(GHGA_ARCHIVE_WORKFLOW.artifacts) - {"added_accessions"}),
)
def test_excluded_files_are_removed_from_artifact(
    artifact: str, artifacts: dict[str, Json]
):
    """No artifact derived from the removal step mentions an excluded file, neither as
    a resource nor as a reference, by accession or by alias.
    """
    serialized = json.dumps(artifacts[artifact])

    for alias, accession in (EXCLUDED_SAMPLE_FILE, EXCLUDED_EXPERIMENT_FILE):
        assert accession not in serialized
        assert alias not in serialized


def test_included_files_remain(artifacts: dict[str, Json]):
    """The removal leaves the included files and the references to them in place."""
    resolved = artifacts["resolved_restricted"]
    dataset = resolved["datasets"][0]

    assert {
        file["accession"]
        for root_slot in ("sample_files", "experiment_files")
        for file in resolved[root_slot]
    } == INCLUDED_ACCESSIONS
    assert dataset["sample_files"] == ["TESTF0000000001", "TESTF0000000002"]
    assert dataset["experiment_files"] == ["TESTF0000000003", "TESTF0000000004"]
    assert set(dataset["files"]) == INCLUDED_ACCESSIONS


def test_excluded_files_are_not_counted(artifacts: dict[str, Json]):
    """The dataset statistics count only the included sample files."""
    stats = artifacts["stats_public"]["dataset_stats"][0]

    assert stats["file_formats"]["stats"] == [{"value": "fastq", "count": 2}]
