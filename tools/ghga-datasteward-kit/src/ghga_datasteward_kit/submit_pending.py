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

"""List the pending submissions, and submit metadata to one of them and complete it.

The pending submission is a reserved study PID, or a `metadata submit` run that
stopped before completing. Either way, the registry steps keep the study PID the
submission already holds.
"""

from collections.abc import Callable
from pathlib import Path

import yaml

from ghga_datasteward_kit.metadata import MetadataConfig, build_submission_registry
from ghga_datasteward_kit.utils import load_config_yaml
from metldata.custom_types import Json
from metldata.submission_registry.models import SubmissionHeader

# handed the current title of the submission, returns whether to submit to it
ConfirmCallback = Callable[[str], bool]


class SubmitPendingAbortedError(Exception):
    """Raised when the user declined to submit the metadata to the submission."""

    def __init__(self):
        super().__init__("Nothing was submitted.")


def submit_pending_metadata(  # noqa: PLR0913
    *,
    submission_id: str,
    study_pid: str,
    submission_title: str,
    submission_description: str,
    metadata: Json,
    config: MetadataConfig,
    confirm: ConfirmCallback,
) -> str:
    """Fill the given pending submission with the metadata and complete it, keeping
    the study PID it holds. Returns the title the submission had before, which for a
    reservation is the internal name of the study.

    A submission that already has content is accepted too, so that a run which
    stopped before completing the submission can be repeated.

    The confirm callback is handed the current title before anything is written,
    since only the user can tell whether the metadata belongs to the submission.

    Raises:
        SubmitPendingAbortedError:
            when the confirm callback declined.
        SubmissionRegistry.SubmissionDoesNotExistError:
            when no submission with the given ID exists.
        SubmissionRegistry.StudyPidMismatchError:
            when the submission does not hold the given study PID.
        SubmissionRegistry.StatusError:
            when the submission is not pending.
        SubmissionRegistry.ValidationError:
            when the metadata failed validation against the metadata model.
        MissingStudyError:
            when the metadata holds no study.
    """
    submission_registry = build_submission_registry(config=config)

    submission_registry.check_study_pid(
        submission_id=submission_id, study_pid=study_pid
    )
    current_title = submission_registry.get_submission(id_=submission_id).title
    if not confirm(current_title):
        raise SubmitPendingAbortedError()

    # refuses a submission that is not pending before validating or minting anything
    submission_registry.upsert_submission_content(
        submission_id=submission_id, content=metadata
    )
    # after the upsert, so that metadata failing validation leaves the current title
    submission_registry.update_submission_header(
        submission_id=submission_id,
        header=SubmissionHeader(
            title=submission_title, description=submission_description
        ),
    )
    submission_registry.complete_submission(id_=submission_id)

    return current_title


def list_pending_submissions_from_path(
    *, config_path: Path
) -> list[tuple[str | None, str, str]]:
    """Read the config from the specified path, then list the pending submissions,
    each as its study PID, or None if it holds none yet, its ID and its title.
    """
    config = load_config_yaml(path=config_path, config_cls=MetadataConfig)
    submission_registry = build_submission_registry(config=config)

    return [
        (study_pid, submission.id, submission.title)
        for submission, study_pid in submission_registry.get_pending_submissions()
    ]


def submit_pending_metadata_from_path(  # noqa: PLR0913
    *,
    submission_id: str,
    study_pid: str,
    submission_title: str,
    submission_description: str,
    metadata_path: Path,
    config_path: Path,
    confirm: ConfirmCallback,
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
        confirm=confirm,
    )
