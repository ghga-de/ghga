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
