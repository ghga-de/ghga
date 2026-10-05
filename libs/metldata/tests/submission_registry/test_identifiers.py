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

from metldata.model_utils.anchors import AnchorPoint
from metldata.submission_registry.identifiers import generate_accession_map


class FakeAccessionRegistry:
    """A fake accession registry."""

    def __init__(self):
        """Initialize with counter to generate predictable accessions."""
        self._counter = 1

    def is_study_class(self, class_name: str) -> bool:
        """Tell whether the given class is the study class."""
        return class_name == "Study"

    def get_study_accession(self, *, predecessor_pid: str | None = None) -> str:
        """Generate the PID of a study."""
        return "generated_study_pid"

    def get_accession(
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
    """Test generating an accession map for a given content."""
    accession_registry = FakeAccessionRegistry()
    content = {
        "study_anchor": [{"alias": "test_study"}],
        "class1_anchor": [{"alias": "test_alias1"}],
        "class2_anchor": [{"alias": "test_alias2"}, {"alias": "test_alias3"}],
    }
    anchor_points_by_target = {
        "Study": AnchorPoint(
            root_slot="study_anchor", target_class="Study", identifier_slot="alias"
        ),
        "Class1": AnchorPoint(
            root_slot="class1_anchor", target_class="Class1", identifier_slot="alias"
        ),
        "Class2": AnchorPoint(
            root_slot="class2_anchor", target_class="Class2", identifier_slot="alias"
        ),
        "Class3": AnchorPoint(
            root_slot="class3_anchor", target_class="Class3", identifier_slot="alias"
        ),
    }
    existing_accession_map = {
        "class2_anchor": {"test_alias2": "existing_class2_accession1"},
        "class3_anchor": {"test_alias3": "existing_class3_accession2"},
    }
    expected_accession_map = {
        "study_anchor": {"test_study": "generated_study_pid"},
        "class1_anchor": {
            "test_alias1": "generated_study_pid.generated_class1_accession1"
        },
        "class2_anchor": {
            "test_alias2": "existing_class2_accession1",
            "test_alias3": "generated_study_pid.generated_class2_accession2",
        },
    }

    observed_accession_map = generate_accession_map(
        content=content,
        existing_accession_map=existing_accession_map,
        accession_registry=accession_registry,  # type: ignore
        anchor_points_by_target=anchor_points_by_target,
    )

    assert observed_accession_map == expected_accession_map
