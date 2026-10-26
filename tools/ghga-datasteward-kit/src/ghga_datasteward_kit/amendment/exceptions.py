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

"""Exceptions raised when amending a submission."""


class AmendmentAbortedError(Exception):
    """Raised when the user declined to apply an amendment."""

    def __init__(self):
        super().__init__("Amendment aborted. Nothing was changed.")


class AmendmentStatusError(Exception):
    """Raised when a submission cannot be amended because of its status."""

    def __init__(self, *, submission_id: str, current_status: str):
        super().__init__(
            f"The submission '{submission_id}' has the status '{current_status}' but"
            " must be 'completed' to be amended."
        )


class StudyAccessionMissingError(Exception):
    """Raised when the stored accession map of a submission holds no study accession,
    so there is none for the new accessions to derive from.
    """

    def __init__(self, *, submission_id: str):
        super().__init__(
            f"The accession map of the submission '{submission_id}' holds no study"
            " accession, so the submission cannot be amended."
        )


class AccessionNotLegacyError(Exception):
    """Raised when the study accession of a submission is not a flat accession, since
    only submissions accessioned before study PIDs can be amended.
    """

    def __init__(self, *, submission_id: str, study_accession: str):
        super().__init__(
            f"The study accession '{study_accession}' of the submission"
            f" '{submission_id}' is not a flat accession, so the submission cannot be"
            " amended."
        )
