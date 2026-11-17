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

"""Reserve a study PID before the metadata of a study arrives, and submit the
metadata under it later.

The reservation is a pending submission without content whose accession map holds
the new study PID. Submitting the metadata fills that submission through the same
registry steps as `metadata submit`, which keep a study PID already in the map.
"""

from pathlib import Path

import yaml

from ghga_datasteward_kit.metadata import MetadataConfig, build_submission_registry
from ghga_datasteward_kit.utils import load_config_yaml
from metldata.custom_types import Json
from metldata.model_utils.essentials import STUDY_ANCHOR
from metldata.submission_registry.models import SubmissionHeader


class StudyPidMismatchError(Exception):
    """Raised when the study PID given for a pending submission is not the one the
    submission holds.
    """

    def __init__(self, *, submission_id: str, study_pid: str):
        super().__init__(
            f"The submission '{submission_id}' does not hold the study PID"
            f" '{study_pid}'. Nothing was submitted."
        )


def reserve_study_pid(
    *,
    submission_title: str,
    submission_description: str | None,
    config: MetadataConfig,
) -> tuple[str, str]:
    """Store a pending submission without content that holds a new study PID.
    Returns the ID of the submission and the study PID.

    The title is the internal name of the study until its metadata arrives.
    """
    submission_registry = build_submission_registry(config=config)

    return submission_registry.reserve_study_pid(
        header=SubmissionHeader(
            title=submission_title, description=submission_description
        )
    )


def submit_pending_metadata(  # noqa: PLR0913
    *,
    submission_id: str,
    study_pid: str,
    submission_title: str,
    submission_description: str,
    metadata: Json,
    config: MetadataConfig,
) -> str:
    """Fill the given pending submission with the metadata and complete it, keeping
    the study PID it holds. Returns the title the submission had before, which for a
    reservation is the internal name of the study.

    A submission that already has content is accepted too, so that a run which
    stopped before completing the submission can be repeated.

    Raises:
        SubmissionRegistry.SubmissionDoesNotExistError:
            when no submission with the given ID exists.
        StudyPidMismatchError:
            when the submission does not hold the given study PID.
        SubmissionRegistry.StatusError:
            when the submission is not pending.
        SubmissionRegistry.ValidationError:
            when the metadata failed validation against the metadata model.
        MissingStudyError:
            when the metadata holds no study.
    """
    submission_registry = build_submission_registry(config=config)

    submission = submission_registry.get_submission(id_=submission_id)
    # the first PID is the one the registry keeps for the study
    stored_pids = submission.accession_map.get(STUDY_ANCHOR, {})
    if next(iter(stored_pids.values()), None) != study_pid:
        raise StudyPidMismatchError(submission_id=submission_id, study_pid=study_pid)

    # refuses a submission that is not pending before validating or minting anything
    submission_registry.upsert_submission_content(
        submission_id=submission_id, content=metadata
    )
    # after the upsert, so that metadata failing validation leaves the internal name
    submission_registry.update_submission_header(
        submission_id=submission_id,
        header=SubmissionHeader(
            title=submission_title, description=submission_description
        ),
    )
    submission_registry.complete_submission(id_=submission_id)

    return submission.title


def reserve_study_pid_from_path(
    *,
    submission_title: str,
    submission_description: str | None,
    config_path: Path,
) -> tuple[str, str]:
    """Read the config from the specified path, then reserve a study PID."""
    config = load_config_yaml(path=config_path, config_cls=MetadataConfig)

    return reserve_study_pid(
        submission_title=submission_title,
        submission_description=submission_description,
        config=config,
    )


def submit_pending_metadata_from_path(  # noqa: PLR0913
    *,
    submission_id: str,
    study_pid: str,
    submission_title: str,
    submission_description: str,
    metadata_path: Path,
    config_path: Path,
) -> str:
    """Read metadata and config from the specified paths, then submit the metadata
    to the given pending submission.
    """
    with open(metadata_path, encoding="utf8") as metadata_file:
        metadata = yaml.safe_load(metadata_file)

    config = load_config_yaml(path=config_path, config_cls=MetadataConfig)

    return submit_pending_metadata(
        submission_id=submission_id,
        study_pid=study_pid,
        submission_title=submission_title,
        submission_description=submission_description,
        metadata=metadata,
        config=config,
    )
