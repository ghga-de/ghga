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

"""Testing the metadata validator."""

from contextlib import nullcontext
from typing import Any

import pytest

from metldata.model_utils.metadata_validator import MetadataValidator
from tests.fixtures.metadata import (
    INVALID_MINIMAL_METADATA_EXAMPLES,
    VALID_MINIMAL_METADATA_EXAMPLES,
)
from tests.fixtures.metadata_models import (
    MINIMAL_MODEL_WITH_STUDY,
    VALID_MINIMAL_METADATA_MODEL,
)


@pytest.mark.parametrize(
    "metadata, is_valid",
    [(valid_metadata, True) for valid_metadata in VALID_MINIMAL_METADATA_EXAMPLES]
    + [
        (invalid_metadata, False)
        for invalid_metadata in INVALID_MINIMAL_METADATA_EXAMPLES
    ],
)
def test_validate_against_model(metadata: dict[str, Any], is_valid: bool):
    """Test the validation of metadata against a model."""
    validator = MetadataValidator(model=VALID_MINIMAL_METADATA_MODEL)

    with (
        nullcontext() if is_valid else pytest.raises(MetadataValidator.ValidationError)
    ):
        validator.validate(metadata)


@pytest.mark.parametrize(
    "studies, expected_message",
    [
        ([], "holds 0 entries, but the model allows at least 1"),
        ([{"alias": "study_1"}], None),
        (
            [{"alias": "study_1"}, {"alias": "study_2"}],
            "holds 2 entries, but the model allows at most 1",
        ),
    ],
    ids=["no_study", "one_study", "two_studies"],
)
def test_validate_one_study_per_submission(
    studies: list[dict[str, Any]], expected_message: str | None
):
    """Test that metadata must hold exactly one study when the model limits the
    studies to one, and that a violation names the field and the limit.
    """
    validator = MetadataValidator(model=MINIMAL_MODEL_WITH_STUDY)
    metadata = {
        "studies": studies,
        "files": [{"alias": "file_1", "filename": "file_1.fastq"}],
    }

    if expected_message is None:
        validator.validate(metadata)
        return

    with pytest.raises(MetadataValidator.ValidationError) as error:
        validator.validate(metadata)

    assert "in field 'studies'" in str(error.value)
    assert expected_message in str(error.value)


@pytest.mark.parametrize(
    "study_alias, file_aliases, shared_alias, expected_message",
    [
        ("study_1", ["file_1", "file_2"], None, None),
        ("sample_1", ["sample_1", "file_2"], "sample_1", "classes 'File', 'Study'"),
        ("study_1", ["file_1", "file_1"], "file_1", "classes 'File', 'File'"),
    ],
    ids=["unique", "shared_across_classes", "shared_within_class"],
)
def test_check_alias_uniqueness(
    study_alias: str,
    file_aliases: list[str],
    shared_alias: str | None,
    expected_message: str | None,
):
    """Test that an alias shared by two entities is rejected, naming the alias and
    the classes sharing it, whether the entities are of different classes or not.
    """
    validator = MetadataValidator(model=MINIMAL_MODEL_WITH_STUDY)
    metadata = {
        "studies": [{"alias": study_alias}],
        "files": [
            {"alias": alias, "filename": f"{alias}.fastq"} for alias in file_aliases
        ],
    }

    if expected_message is None:
        validator.check_alias_uniqueness(metadata)
        return

    with pytest.raises(MetadataValidator.ValidationError) as error:
        validator.check_alias_uniqueness(metadata)

    assert f"with value '{shared_alias}'" in str(error.value)
    assert expected_message in str(error.value)
