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

"""Test completing the accession map in the metadata_transform module."""

import pytest

from metldata.builtin_transformations.add_accessions.metadata_transform import (
    complete_accession_map,
    compose_accession,
)
from metldata.model_utils.anchors import AnchorPoint
from metldata.transform.base import MetadataTransformationError

STUDY_PID = "GHGA.26.K7Q.1"
DATASET_PID = f"{STUDY_PID}.DS.M3P"

ANCHOR_POINTS_BY_TARGET = {
    class_name: AnchorPoint(
        target_class=class_name, root_slot=root_slot, identifier_slot="alias"
    )
    for class_name, root_slot in {
        "Study": "studies",
        "Dataset": "datasets",
        "Sample": "samples",
    }.items()
}

METADATA = {
    "studies": [{"alias": "STUDY_A"}],
    "datasets": [{"alias": "DS_A"}],
    "samples": [{"alias": "Sample.01"}, {"alias": "SAMPLE_2"}],
}


def complete(accession_map: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    """Complete the accession map of the test metadata."""
    return complete_accession_map(
        metadata=METADATA,
        accession_map=accession_map,
        anchor_points_by_target=ANCHOR_POINTS_BY_TARGET,
        study_class_name="Study",
    )


def test_compose_accession():
    """The alias is normalized, so it cannot add a further block to the PID."""
    assert (
        compose_accession(study_pid=STUDY_PID, alias=" Reads_R1.fastq.gz ")
        == f"{STUDY_PID}.reads_r1-fastq-gz"
    )


def test_missing_classes_composed():
    """A class missing from the map gets accessions composed from the study PID,
    while the study and the dataset keep their stored accessions.
    """
    accession_map = {
        "studies": {"STUDY_A": STUDY_PID},
        "datasets": {"DS_A": DATASET_PID},
    }

    assert complete(accession_map) == {
        **accession_map,
        "samples": {
            "Sample.01": f"{STUDY_PID}.sample-01",
            "SAMPLE_2": f"{STUDY_PID}.sample_2",
        },
    }


def test_stored_classes_kept():
    """A map holding every class is returned as it is, so a flat-accessioned map
    needs no study PID at all.
    """
    accession_map = {
        "studies": {"STUDY_A": "GHGAS00000000000001"},
        "datasets": {"DS_A": "GHGAD00000000000001"},
        "samples": {
            "Sample.01": "GHGAN00000000000001",
            "SAMPLE_2": "GHGAN00000000000002",
        },
    }

    assert complete(accession_map) == accession_map


@pytest.mark.parametrize(
    "study_accessions",
    [{}, {"STUDY_A": STUDY_PID, "STUDY_B": "GHGA.26.ABC.1"}],
    ids=["no_study", "two_studies"],
)
def test_not_one_study_accession(study_accessions: dict[str, str]):
    """Composing needs exactly one study accession in the map."""
    accession_map = {"studies": study_accessions, "datasets": {"DS_A": DATASET_PID}}

    with pytest.raises(MetadataTransformationError, match="exactly one accession"):
        complete(accession_map)


def test_flat_study_accession():
    """A flat study accession is not composed from, so a flat-accessioned map
    missing a class fails.
    """
    accession_map = {
        "studies": {"STUDY_A": "GHGAS00000000000001"},
        "datasets": {"DS_A": "GHGAD00000000000001"},
    }

    with pytest.raises(MetadataTransformationError, match="not a study PID"):
        complete(accession_map)


def test_no_study_class():
    """Composing fails for a model without the configured study class."""
    with pytest.raises(MetadataTransformationError, match="no anchored study class"):
        complete_accession_map(
            metadata=METADATA,
            accession_map={"studies": {"STUDY_A": STUDY_PID}},
            anchor_points_by_target=ANCHOR_POINTS_BY_TARGET,
            study_class_name="Investigation",
        )
