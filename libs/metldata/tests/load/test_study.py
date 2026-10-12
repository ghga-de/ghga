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

"""Test the rule that a publishable artifact holds exactly one study."""

import pytest

from metldata.custom_types import Json
from metldata.load.study import StudyCountError, get_single_study_accession


def test_single_study():
    """The accession of the one study is returned."""
    content = {"studies": [{"accession": "GHGAS1"}], "samples": []}

    assert get_single_study_accession(content) == "GHGAS1"


@pytest.mark.parametrize(
    "content, expected_message",
    [
        ({"samples": []}, "Expected exactly one study, found 0."),
        ({"studies": []}, "Expected exactly one study, found 0."),
        (
            {"studies": [{"accession": "GHGAS1"}, {"accession": "GHGAS2"}]},
            "Expected exactly one study, found 2: GHGAS1, GHGAS2.",
        ),
        ({"studies": [{"alias": "STUDY_1"}]}, "The study has no accession."),
    ],
    ids=["no_studies_key", "no_study", "two_studies", "no_accession"],
)
def test_not_single_study(content: Json, expected_message: str):
    """Content without exactly one study with an accession is rejected."""
    with pytest.raises(StudyCountError) as error:
        get_single_study_accession(content)

    assert str(error.value) == expected_message
