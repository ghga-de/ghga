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

"""Test the delete_resources transformation beyond the fixture-driven cases."""

from pathlib import Path

import pytest
import yaml

from metldata.builtin_transformations.delete_resources import (
    RESOURCE_DELETION_TRANSFORMATION,
    ResourceDeletionConfig,
)
from metldata.builtin_transformations.delete_resources.metadata_transform import (
    delete_resources,
)
from metldata.model_utils.anchors import get_anchors_points_by_target
from metldata.model_utils.assumptions import MetadataModelAssumptionError
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import MetadataTransformationError
from tests.fixtures.utils import BASE_DIR, read_yaml

MODEL_PATH = (
    BASE_DIR
    / "transformations"
    / "delete_resources"
    / "with_references"
    / "original_model.yaml"
)


def test_single_valued_reference_to_deleted_resource_raises(tmp_path: Path):
    """A single-valued reference cannot be pruned, so deleting its target fails."""
    model_dict = read_yaml(MODEL_PATH)
    model_dict["classes"]["Report"] = {
        "slots": ["alias", "file"],
        "slot_usage": {
            "alias": {"required": True, "identifier": True},
            "file": {"required": True, "inlined": False},
        },
    }
    model_dict["slots"]["file"] = {"range": "File"}
    model_dict["slots"]["reports"] = {"range": "Report"}
    model_dict["classes"]["Submission"]["slots"].append("reports")
    model_dict["classes"]["Submission"]["slot_usage"]["reports"] = {
        "required": True,
        "multivalued": True,
        "inlined": True,
        "inlined_as_list": True,
    }
    model_path = tmp_path / "model.yaml"
    model_path.write_text(yaml.safe_dump(model_dict))
    model = MetadataModel.init_from_path(model_path)

    metadata = {
        "files": [
            {"alias": "F1", "name": "file_1.fastq.gz", "included_in_submission": True},
            {"alias": "F2", "name": "file_2.fastq.gz", "included_in_submission": False},
        ],
        "analyses": [{"alias": "A1", "files": ["F1", "F2"]}],
        "reports": [{"alias": "R1", "file": "F2"}],
    }

    with pytest.raises(MetadataTransformationError, match=r"'file'.*'Report'.*'F2'"):
        delete_resources(
            metadata=metadata,
            resources_to_delete={"File": {"included_in_submission": False}},
            anchor_points_by_target=get_anchors_points_by_target(model=model),
            schema_view=model.schema_view,
        )


@pytest.fixture(name="model", scope="module")
def model_fixture() -> MetadataModel:
    """Provide the model of the with_references case."""
    return MetadataModel.init_from_path(MODEL_PATH)


def _delete(metadata, conditions, model: MetadataModel):
    """Delete the files matching the conditions from the metadata."""
    return delete_resources(
        metadata=metadata,
        resources_to_delete={"File": conditions},
        anchor_points_by_target=get_anchors_points_by_target(model=model),
        schema_view=model.schema_view,
    )


def test_all_conditions_must_match(model: MetadataModel):
    """A resource is deleted only when every configured slot carries its value."""
    metadata = {
        "files": [
            {"alias": "F1", "name": "keep.txt", "included_in_submission": False},
            {"alias": "F2", "name": "drop.txt", "included_in_submission": False},
            {"alias": "F3", "name": "drop.txt", "included_in_submission": True},
        ],
        "analyses": [{"alias": "A1", "files": ["F1", "F2", "F3"]}],
    }

    transformed = _delete(
        metadata, {"included_in_submission": False, "name": "drop.txt"}, model
    )

    assert [file["alias"] for file in transformed["files"]] == ["F1", "F3"]
    assert transformed["analyses"] == [{"alias": "A1", "files": ["F1", "F3"]}]


@pytest.mark.parametrize(
    "conditions",
    [{}, {"included_in_submission": False}],
    ids=["no_conditions", "no_match"],
)
def test_nothing_deleted(conditions: dict, model: MetadataModel):
    """Without conditions or without a marked resource the metadata stay as they are."""
    metadata = {
        "files": [
            {"alias": "F1", "name": "file_1.fastq.gz", "included_in_submission": True},
            {"alias": "F2", "name": "file_2.fastq.gz"},
        ],
        "analyses": [{"alias": "A1", "files": ["F1", "F2"]}],
    }

    assert _delete(metadata, conditions, model) == metadata


def test_input_metadata_not_modified(model: MetadataModel):
    """The transformation works on a copy."""
    metadata = {
        "files": [
            {"alias": "F1", "name": "file_1.fastq.gz", "included_in_submission": False}
        ],
        "analyses": [{"alias": "A1", "files": ["F1"]}],
    }
    original = yaml.safe_load(yaml.safe_dump(metadata))

    transformed = _delete(metadata, {"included_in_submission": False}, model)

    assert transformed == {"files": [], "analyses": [{"alias": "A1", "files": []}]}
    assert metadata == original


@pytest.mark.parametrize(
    "resources_to_delete, message",
    [
        ({"Unknown": {"included_in_submission": False}}, "anchor points"),
        ({"File": {"unknown_slot": False}}, "'unknown_slot'.*'File'"),
    ],
    ids=["unknown_class", "unknown_slot"],
)
def test_model_assumptions(
    resources_to_delete: dict, message: str, model: MetadataModel
):
    """A class without an anchor point or a slot the class lacks is rejected."""
    config = ResourceDeletionConfig(resources_to_delete=resources_to_delete)

    with pytest.raises(MetadataModelAssumptionError, match=message):
        RESOURCE_DELETION_TRANSFORMATION.check_model_assumptions(model, config)
