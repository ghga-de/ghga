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

"""Testing the assumptions module."""

from contextlib import nullcontext

import pytest
import yaml

from metldata.model_utils.assumptions import (
    MetadataModelAssumptionError,
    check_basic_model_assumption,
    check_class_exists,
    check_class_slot_exists,
    check_governance_anchors,
    check_study_anchor,
    check_study_cardinality,
)
from metldata.model_utils.essentials import MetadataModel
from tests.fixtures.metadata_models import (
    INVALID_METADATA_MODELS,
    MINIMAL_MODEL_WITH_OPTIONAL_STUDY,
    MINIMAL_MODEL_WITH_RENAMED_STUDY_ANCHOR,
    MINIMAL_MODEL_WITH_STUDY,
    MINIMAL_MODEL_WITH_STUDY_PATH,
    MINIMAL_MODEL_WITH_UNBOUNDED_STUDIES,
    VALID_ADVANCED_METADATA_MODEL,
    VALID_METADATA_MODELS,
    VALID_MINIMAL_METADATA_MODEL,
)


@pytest.mark.parametrize(
    "model, is_valid",
    [(valid_model, True) for valid_model in VALID_METADATA_MODELS]
    + [(invalid_model, False) for invalid_model in INVALID_METADATA_MODELS],
)
def test_metadata_model_assumption_checking(model: MetadataModel, is_valid: bool):
    """Test the assumptions regarding the metadata model are correctly checked."""
    with nullcontext() if is_valid else pytest.raises(MetadataModelAssumptionError):
        check_basic_model_assumption(model)


@pytest.mark.parametrize(
    "model, class_name, exists",
    [
        (VALID_MINIMAL_METADATA_MODEL, "Dataset", True),
        (VALID_MINIMAL_METADATA_MODEL, "NotExistingClass", False),
    ],
)
def test_check_class_exists(model: MetadataModel, class_name: str, exists: bool):
    """Test the check_class_exists function."""
    with nullcontext() if exists else pytest.raises(MetadataModelAssumptionError):
        check_class_exists(model=model, class_name=class_name)


@pytest.mark.parametrize(
    "model, class_name, slot_name, ignore_parents, exists",
    [
        (VALID_MINIMAL_METADATA_MODEL, "Dataset", "alias", False, True),
        (VALID_MINIMAL_METADATA_MODEL, "Dataset", "alias", True, False),
        (VALID_MINIMAL_METADATA_MODEL, "Dataset", "files", True, True),
        (VALID_MINIMAL_METADATA_MODEL, "Dataset", "not_existing_slot", False, False),
        (VALID_MINIMAL_METADATA_MODEL, "NotExistingClass", "name", False, False),
    ],
)
def test_check_class_slot_exists(
    model: MetadataModel,
    class_name: str,
    slot_name: str,
    ignore_parents: bool,
    exists: bool,
):
    """Test the check_class_slot_exists function."""
    with nullcontext() if exists else pytest.raises(MetadataModelAssumptionError):
        check_class_slot_exists(
            model=model,
            class_name=class_name,
            slot_name=slot_name,
            ignore_parents=ignore_parents,
        )


@pytest.mark.parametrize(
    "model, is_valid",
    [
        (MINIMAL_MODEL_WITH_STUDY, True),
        (MINIMAL_MODEL_WITH_RENAMED_STUDY_ANCHOR, False),  # not anchored on studies
        (VALID_MINIMAL_METADATA_MODEL, False),  # has no study class
    ],
)
def test_check_study_anchor(model: MetadataModel, is_valid: bool):
    """Test that only a model anchoring the study on STUDY_ANCHOR passes."""
    with nullcontext() if is_valid else pytest.raises(MetadataModelAssumptionError):
        check_study_anchor(model=model)


@pytest.mark.parametrize(
    "model, is_valid",
    [
        (MINIMAL_MODEL_WITH_STUDY, True),
        (MINIMAL_MODEL_WITH_UNBOUNDED_STUDIES, False),
        (MINIMAL_MODEL_WITH_OPTIONAL_STUDY, False),  # studies is not required
        (VALID_MINIMAL_METADATA_MODEL, False),  # has no studies slot
    ],
)
def test_check_study_cardinality(model: MetadataModel, is_valid: bool):
    """Test that only a model with exactly one study per submission passes."""
    with nullcontext() if is_valid else pytest.raises(MetadataModelAssumptionError):
        check_study_cardinality(model=model)


def _rename_slot(*, class_name: str, old_name: str, new_name: str) -> MetadataModel:
    """Return the minimal model with a study, with a slot of a class renamed."""
    model_json = yaml.safe_load(MINIMAL_MODEL_WITH_STUDY_PATH.read_text())
    class_ = model_json["classes"][class_name]
    class_["slots"] = [
        new_name if slot_name == old_name else slot_name
        for slot_name in class_["slots"]
    ]
    class_["slot_usage"][new_name] = class_["slot_usage"].pop(old_name)
    model_json["slots"][new_name] = model_json["slots"].pop(old_name)
    return MetadataModel(**model_json)


@pytest.mark.parametrize(
    "model, is_valid",
    [
        (MINIMAL_MODEL_WITH_STUDY, True),
        # the root slots come from the anchor points, so they may differ:
        (
            _rename_slot(
                class_name="Submission",
                old_name="data_access_policies",
                new_name="access_policies",
            ),
            True,
        ),
        # the traversal follows the slots linking the classes, so they may not:
        (
            _rename_slot(
                class_name="DataAccessPolicy",
                old_name="data_access_committee",
                new_name="committee",
            ),
            False,
        ),
        (VALID_ADVANCED_METADATA_MODEL, False),  # has no data access policy class
    ],
    ids=["valid", "renamed_root_slot", "renamed_link_slot", "no_policy_class"],
)
def test_check_governance_anchors(model: MetadataModel, is_valid: bool):
    """Test that only a model with the governance chain passes."""
    with nullcontext() if is_valid else pytest.raises(MetadataModelAssumptionError):
        check_governance_anchors(model=model)
