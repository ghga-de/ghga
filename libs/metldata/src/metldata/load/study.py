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
from metldata.model_utils.essentials import STUDY_ANCHOR


class InvalidStudyError(ValueError):
    """Raised when an artifact does not hold exactly one well-formed study."""


def get_single_study_accession(content: Json) -> str:
    """Return the accession of the one study in an artifact's `content` field, which
    holds the artifact's resources keyed by anchor. The study is read from the
    STUDY_ANCHOR slot, which check_study_anchor enforces on the model.

    Both the loader client and the loader API call this, so that they apply the same
    rule to the artifacts published whole.

    Raises:
        InvalidStudyError: If the studies are not a list of objects, the content holds
            no study or more than one, or the study has no accession string.
    """
    # the loader API validates content only as a JSON object, so the values inside
    # it can be any JSON, and a type error here would surface as a 500
    studies = content.get(STUDY_ANCHOR, [])
    if not isinstance(studies, list):
        raise InvalidStudyError(
            f"Expected a list under '{STUDY_ANCHOR}', found {type(studies).__name__}."
        )
    if not all(isinstance(study, dict) for study in studies):
        raise InvalidStudyError(
            f"Expected every item under '{STUDY_ANCHOR}' to be an object."
        )

    if len(studies) != 1:
        accessions = ", ".join(str(study.get("accession")) for study in studies)
        raise InvalidStudyError(
            f"Expected exactly one study, found {len(studies)}"
            + (f": {accessions}." if accessions else ".")
        )

    accession = studies[0].get("accession")
    if not accession:
        raise InvalidStudyError("The study has no accession.")
    if not isinstance(accession, str):
        raise InvalidStudyError(
            "Expected the study accession to be a string, found"
            + f" {type(accession).__name__}."
        )

    return accession
