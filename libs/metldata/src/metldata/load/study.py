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

"""The rule that an artifact published whole holds exactly one study."""

from metldata.custom_types import Json


class StudyCountError(ValueError):
    """Raised when an artifact does not hold exactly one study."""


def get_single_study_accession(content: Json) -> str:
    """Return the accession of the one study in an artifact's `content` field, which
    holds the artifact's resources keyed by anchor, e.g. 'studies'.

    Both the loader client and the loader API call this, so that they apply the same
    rule to the artifacts published whole.

    Raises:
        StudyCountError: If the content holds no study or more than one, or the study
            has no accession.
    """
    studies = content.get("studies", [])
    if len(studies) != 1:
        accessions = ", ".join(str(study.get("accession")) for study in studies)
        raise StudyCountError(
            f"Expected exactly one study, found {len(studies)}"
            + (f": {accessions}." if accessions else ".")
        )

    accession = studies[0].get("accession")
    if not accession:
        raise StudyCountError("The study has no accession.")

    return accession
