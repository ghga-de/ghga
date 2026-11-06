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
"""Test the identifiers module."""

import pytest

from metldata.accession_registry import accession_registry as accession_registry_module
from metldata.accession_registry.accession_registry import AccessionRegistry
from metldata.accession_registry.accession_store import AccessionStore
from metldata.config import SubmissionConfig
from metldata.model_utils.anchors import AnchorPoint
from metldata.submission_registry.identifiers import generate_accession_map
from tests.fixtures.config import config_sub_fixture  # noqa: F401


class FakeAccessionRegistry:
    """A fake accession registry."""

    def __init__(self):
        """Initialize with counter to generate predictable accessions."""
        self._counter = 1

    def is_study_class(self, class_name: str) -> bool:
        """Tell whether the given class is the study class."""
        return class_name == "Study"

    def is_dataset_class(self, class_name: str) -> bool:
        """Tell whether the given class is the dataset class."""
        return class_name == "Dataset"

    def generate_study_accession(self) -> str:
        """Generate the PID of a study."""
        return "generated_study_pid"

    def generate_accession(
        self, *, class_name: str, alias: str, study_pid: str, used_accessions: set[str]
    ) -> str:
        """Generate the accession of a resource of the specified class in a study."""
        if self.is_study_class(class_name):
            return study_pid

        accession = (
            f"{study_pid}.generated_{class_name.lower()}_accession{self._counter}"
        )
        self._counter += 1

        return accession


def test_generate_accession_map():
    """Test that the accession map holds the study and dataset accessions only: a
    dataset still in the content keeps its accession, a new one gets one, a removed
    one is dropped, and a class that is neither study nor dataset is left out.
    """
    accession_registry = FakeAccessionRegistry()
    content = {
        "study_anchor": [{"alias": "test_study"}],
        "dataset_anchor": [{"alias": "DS_A"}, {"alias": "DS_B"}],
        "class1_anchor": [{"alias": "test_alias1"}],
    }
    anchor_points_by_target = {
        "Study": AnchorPoint(
            root_slot="study_anchor", target_class="Study", identifier_slot="alias"
        ),
        "Dataset": AnchorPoint(
            root_slot="dataset_anchor", target_class="Dataset", identifier_slot="alias"
        ),
        "Class1": AnchorPoint(
            root_slot="class1_anchor", target_class="Class1", identifier_slot="alias"
        ),
    }
    existing_accession_map = {
        "dataset_anchor": {
            "DS_A": "existing_dataset_accession1",
            "DS_C": "existing_dataset_accession2",
        },
    }
    expected_accession_map = {
        "study_anchor": {"test_study": "generated_study_pid"},
        "dataset_anchor": {
            "DS_A": "existing_dataset_accession1",
            "DS_B": "generated_study_pid.generated_dataset_accession1",
        },
    }

    observed_accession_map = generate_accession_map(
        content=content,
        existing_accession_map=existing_accession_map,
        accession_registry=accession_registry,  # type: ignore
        anchor_points_by_target=anchor_points_by_target,
    )

    assert observed_accession_map == expected_accession_map


def test_new_study_alias_keeps_pid():
    """A study given a new alias between two upserts keeps its PID, now under the
    new alias, so the dataset accessions keep their prefix.
    """
    content = {
        "study_anchor": [{"alias": "new_study_alias"}],
        "dataset_anchor": [{"alias": "DS_A"}],
    }
    anchor_points_by_target = {
        "Study": AnchorPoint(
            root_slot="study_anchor", target_class="Study", identifier_slot="alias"
        ),
        "Dataset": AnchorPoint(
            root_slot="dataset_anchor", target_class="Dataset", identifier_slot="alias"
        ),
    }
    existing_accession_map = {
        "study_anchor": {"test_study": "existing_study_pid"},
        "dataset_anchor": {"DS_A": "existing_study_pid.DS.ABC"},
    }

    observed_accession_map = generate_accession_map(
        content=content,
        existing_accession_map=existing_accession_map,
        accession_registry=FakeAccessionRegistry(),  # type: ignore
        anchor_points_by_target=anchor_points_by_target,
    )

    assert observed_accession_map == {
        "study_anchor": {"new_study_alias": "existing_study_pid"},
        "dataset_anchor": {"DS_A": "existing_study_pid.DS.ABC"},
    }


def test_existing_dataset_pid_not_drawn_again(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
):
    """A new dataset never gets the PID of a dataset already in the map, even when
    the random draw hits it.
    """
    draws = iter(["K7Q", "M2X"])
    monkeypatch.setattr(
        accession_registry_module, "generate_random_block", lambda *_: next(draws)
    )
    anchor_points_by_target = {
        "Study": AnchorPoint(
            root_slot="study_anchor", target_class="Study", identifier_slot="alias"
        ),
        "Dataset": AnchorPoint(
            root_slot="dataset_anchor", target_class="Dataset", identifier_slot="alias"
        ),
    }

    accession_map = generate_accession_map(
        content={
            "study_anchor": [{"alias": "test_study"}],
            "dataset_anchor": [{"alias": "DS_A"}, {"alias": "DS_B"}],
        },
        existing_accession_map={
            "study_anchor": {"test_study": "GHGA.26.ABC.1"},
            "dataset_anchor": {"DS_A": "GHGA.26.ABC.1.DS.K7Q"},
        },
        accession_registry=AccessionRegistry(
            config=config_sub_fixture,
            accession_store=AccessionStore(config=config_sub_fixture),
        ),
        anchor_points_by_target=anchor_points_by_target,
    )

    assert accession_map["dataset_anchor"] == {
        "DS_A": "GHGA.26.ABC.1.DS.K7Q",
        "DS_B": "GHGA.26.ABC.1.DS.M2X",
    }
