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
from metldata.metadata_utils import normalize_alias
from metldata.model_utils.anchors import AnchorPoint
from metldata.model_utils.metadata_validator import MetadataValidator
from metldata.submission_registry.identifiers import generate_accession_map
from tests.fixtures.config import config_sub_fixture  # noqa: F401


class FakeAccessionRegistry:
    """A fake accession registry."""

    def __init__(self, *, retired: set[str] | None = None):
        """Initialize with counter to generate predictable accessions, and with the
        accessions retired so far.
        """
        self._counter = 1
        self.retired = set(retired or ())

    def get_retired_accessions(self, *, study_pid: str) -> set[str]:
        """Get the accessions the study retired."""
        return set(self.retired)

    def retire_accessions(self, *, study_pid: str, accessions: set[str]) -> None:
        """Register the accessions the study dropped."""
        self.retired |= accessions

    def is_study_class(self, class_name: str) -> bool:
        """Tell whether the given class is the study class."""
        return class_name == "Study"

    def get_study_accession(self) -> str:
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


def test_new_study_alias_keeps_pid():
    """A study given a new alias between two upserts keeps its PID, now under the
    new alias, so the other accessions keep their prefix.
    """
    content = {
        "study_anchor": [{"alias": "new_study_alias"}],
        "class1_anchor": [{"alias": "test_alias1"}],
    }
    anchor_points_by_target = {
        "Study": AnchorPoint(
            root_slot="study_anchor", target_class="Study", identifier_slot="alias"
        ),
        "Class1": AnchorPoint(
            root_slot="class1_anchor", target_class="Class1", identifier_slot="alias"
        ),
    }
    existing_accession_map = {
        "study_anchor": {"test_study": "existing_study_pid"},
        "class1_anchor": {"test_alias1": "existing_study_pid.test_alias1"},
    }

    observed_accession_map = generate_accession_map(
        content=content,
        existing_accession_map=existing_accession_map,
        accession_registry=FakeAccessionRegistry(),  # type: ignore
        anchor_points_by_target=anchor_points_by_target,
    )

    assert observed_accession_map == {
        "study_anchor": {"new_study_alias": "existing_study_pid"},
        "class1_anchor": {"test_alias1": "existing_study_pid.test_alias1"},
    }


class AliasAccessionRegistry(FakeAccessionRegistry):
    """A fake accession registry composing '{study_pid}.{alias}' from the normalized
    alias, as the real one does.
    """

    def get_accession(
        self, *, class_name: str, alias: str, study_pid: str, used_accessions: set[str]
    ) -> str:
        """Compose the accession of a resource from its normalized alias."""
        if self.is_study_class(class_name):
            return study_pid
        return f"{study_pid}.{normalize_alias(alias)}"


def test_dropped_alias_accession_not_reused():
    """A new alias that normalizes like a dropped one is rejected, naming the dropped
    alias, since its accession would pass to another entity.
    """
    content = {
        "study_anchor": [{"alias": "test_study"}],
        "class1_anchor": [{"alias": "reads-bam"}],
    }
    anchor_points_by_target = {
        "Study": AnchorPoint(
            root_slot="study_anchor", target_class="Study", identifier_slot="alias"
        ),
        "Class1": AnchorPoint(
            root_slot="class1_anchor", target_class="Class1", identifier_slot="alias"
        ),
    }
    existing_accession_map = {
        "study_anchor": {"test_study": "existing_study_pid"},
        "class1_anchor": {"reads.bam": "existing_study_pid.reads-bam"},
    }

    accession_registry = AliasAccessionRegistry()

    with pytest.raises(MetadataValidator.ValidationError) as error:
        generate_accession_map(
            content=content,
            existing_accession_map=existing_accession_map,
            accession_registry=accession_registry,  # type: ignore
            anchor_points_by_target=anchor_points_by_target,
        )

    assert "with value 'reads-bam'" in str(error.value)
    assert (
        "which belonged to 'reads.bam' before; keep that alias or choose a different"
        in str(error.value)
    )
    # refused before the map was complete, so the dropped alias retires nothing
    assert accession_registry.retired == set()


ANCHOR_POINTS_WITH_STUDY = {
    "Study": AnchorPoint(
        root_slot="study_anchor", target_class="Study", identifier_slot="alias"
    ),
    "Class1": AnchorPoint(
        root_slot="class1_anchor", target_class="Class1", identifier_slot="alias"
    ),
}


def test_retired_accession_not_reused():
    """A new alias that would get an accession the study retired is rejected, even
    though no alias in the existing map holds it any more.
    """
    content = {
        "study_anchor": [{"alias": "test_study"}],
        "class1_anchor": [{"alias": "Sample A"}],
    }
    existing_accession_map = {"study_anchor": {"test_study": "existing_study_pid"}}

    with pytest.raises(MetadataValidator.ValidationError) as error:
        generate_accession_map(
            content=content,
            existing_accession_map=existing_accession_map,
            accession_registry=AliasAccessionRegistry(  # type: ignore
                retired={"existing_study_pid.sample-a"}
            ),
            anchor_points_by_target=ANCHOR_POINTS_WITH_STUDY,
        )

    assert "with value 'Sample A'" in str(error.value)
    assert "which the study dropped before and never gives out again" in str(
        error.value
    )


def test_retired_dataset_pid_not_drawn_again(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
):
    """A new dataset never gets a dataset PID the study retired, even when the random
    draw hits it, since access grants keyed by the PID would pass to the new dataset.
    """
    accession_store = AccessionStore(config=config_sub_fixture)
    accession_store.retire(year="26", random_block="ABC", retired=["DS.K7Q"])
    draws = iter(["K7Q", "M2X"])
    monkeypatch.setattr(
        accession_registry_module, "generate_random_block", lambda *_: next(draws)
    )
    content = {
        "study_anchor": [{"alias": "test_study"}],
        "dataset_anchor": [{"alias": "DS_B"}],
    }
    anchor_points_by_target = {
        "Study": AnchorPoint(
            root_slot="study_anchor", target_class="Study", identifier_slot="alias"
        ),
        "Dataset": AnchorPoint(
            root_slot="dataset_anchor", target_class="Dataset", identifier_slot="alias"
        ),
    }

    accession_map = generate_accession_map(
        content=content,
        existing_accession_map={"study_anchor": {"test_study": "GHGA.26.ABC.1"}},
        accession_registry=AccessionRegistry(
            config=config_sub_fixture, accession_store=accession_store
        ),
        anchor_points_by_target=anchor_points_by_target,
    )

    assert accession_map["dataset_anchor"] == {"DS_B": "GHGA.26.ABC.1.DS.M2X"}


def test_dropped_accessions_retired():
    """The accessions the existing map loses are retired, but not the study PID,
    which stays under the study's new alias.
    """
    content = {
        "study_anchor": [{"alias": "new_study_alias"}],
        "class1_anchor": [{"alias": "sample_b"}],
    }
    existing_accession_map = {
        "study_anchor": {"test_study": "existing_study_pid"},
        "class1_anchor": {
            "sample_a": "existing_study_pid.sample_a",
            "sample_b": "existing_study_pid.sample_b",
        },
    }
    accession_registry = FakeAccessionRegistry()

    generate_accession_map(
        content=content,
        existing_accession_map=existing_accession_map,
        accession_registry=accession_registry,  # type: ignore
        anchor_points_by_target=ANCHOR_POINTS_WITH_STUDY,
    )

    assert accession_registry.retired == {"existing_study_pid.sample_a"}
