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

"""Logic for handling submissions."""

from ghga_service_commons.utils.utc_dates import now_as_utc
from metldata.accession_registry.accession_registry import AccessionRegistry
from metldata.custom_types import SubmissionContent
from metldata.model_utils.anchors import get_anchors_points_by_target
from metldata.model_utils.config import MetadataModelConfig
from metldata.model_utils.metadata_validator import MetadataValidator
from metldata.submission_registry import models
from metldata.submission_registry.event_publisher import SourceEventPublisher
from metldata.submission_registry.identifiers import (
    generate_accession_map,
    generate_submission_id,
    lookup_study_pid,
)
from metldata.submission_registry.submission_store import SubmissionStore


class SubmissionRegistryConfig(MetadataModelConfig):
    """Config parameters and their defaults."""


class SubmissionRegistry:
    """A class for handling submissions."""

    # error shortcuts:
    SubmissionDoesNotExistError = SubmissionStore.SubmissionDoesNotExistError
    ValidationError = MetadataValidator.ValidationError

    class StatusError(RuntimeError):
        """Raised when the requested action requires a different submission status."""

        def __init__(
            self, *, submission_id: str, current_status: str, expected_status: str
        ):
            message = (
                f"The submission with id '{submission_id}' has the status"
                + f" '{current_status}' but expected '{expected_status}'."
            )
            super().__init__(message)

    class ContentEmptyError(RuntimeError):
        """Raised when the content of a submission is empty.."""

        def __init__(self, *, submission_id: str):
            message = (
                f"The content for the submission with id '{submission_id}' has not yet"
                + " been specified."
            )
            super().__init__(message)

    class StudyPidMismatchError(RuntimeError):
        """Raised when a submission does not hold the study PID it is expected to."""

        def __init__(self, *, submission_id: str, study_pid: str):
            message = (
                f"The submission '{submission_id}' does not hold the study PID"
                + f" '{study_pid}'."
            )
            super().__init__(message)

    def __init__(
        self,
        *,
        config: SubmissionRegistryConfig,
        submission_store: SubmissionStore,
        event_publisher: SourceEventPublisher,
        accession_registry: AccessionRegistry,
    ):
        """Initialize with dependencies and config parameters."""
        self._submission_store = submission_store
        self._metadata_validator = MetadataValidator(model=config.metadata_model)
        self._event_publisher = event_publisher
        self._accession_registry = accession_registry
        self._anchor_points_by_target = get_anchors_points_by_target(
            model=config.metadata_model
        )
        self._study_anchor = self._anchor_points_by_target[
            config.study_class_name
        ].root_slot

    def _get_submission_with_status(
        self, *, id_: str, expected_status: models.SubmissionStatus
    ) -> models.Submission:
        """Get details for a submission that is assumed to have the specified status.

        Raises:
            SubmissionRegistry.SubmissionDoesNotExistError:
                when no submission with the specified ID exists.
            SubmissionRegistry.StatusError:
                when the submission does not have the expected status.
        """
        # raises SubmissionDoesNotExistError if failed to get submission by id:
        submission = self._submission_store.get_by_id(submission_id=id_)

        if submission.current_status != expected_status:
            raise self.StatusError(
                submission_id=id_,
                current_status=submission.current_status.value,
                expected_status=expected_status.value,
            )

        return submission

    def init_submission(self, *, header: models.SubmissionHeader) -> str:
        """Initialize a new submission by providing header information. Returns the
        ID of the created submission. No source event is published, yet, since the
        submission content is still empty.
        """
        id_ = generate_submission_id()
        submission_creation = models.Submission(id=id_, **header.model_dump())
        self._submission_store.insert_new(submission=submission_creation)

        return id_

    def reserve_study_pid(self, *, header: models.SubmissionHeader) -> tuple[str, str]:
        """Initialize a new submission that holds a new study PID, so the PID can be
        handed out before the metadata exists. Returns the ID of the created
        submission and the study PID. No source event is published, since the
        submission content is still empty.

        The PID is filed under itself as alias, since the study alias is not known
        yet. Upserting the content keeps it, whatever its alias, and files it under
        the alias of the study in the content.

        Raises:
            AccessionRegistry.AccessionGenerationError:
                when every study PID of the year is taken.
        """
        # minted before the submission is stored, so a failure leaves at most an
        # unused PID, never a submission without one
        study_pid = self._accession_registry.generate_study_accession()
        submission_creation = models.Submission(
            id=generate_submission_id(),
            **header.model_dump(),
            accession_map={self._study_anchor: {study_pid: study_pid}},
        )
        self._submission_store.insert_new(submission=submission_creation)

        return submission_creation.id, study_pid

    def get_submission(self, *, id_: str) -> models.Submission:
        """Get details on the existing submission with the specified id.

        Raises:
            SubmissionRegistry.SubmissionDoesNotExistError:
                when no submission with the specified ID exists.
        """
        return self._submission_store.get_by_id(id_)

    def check_study_pid(self, *, submission_id: str, study_pid: str) -> None:
        """Check that the existing submission with the specified id holds the provided
        study PID, so that content meant for one study is not added to another.

        Raises:
            SubmissionRegistry.SubmissionDoesNotExistError:
                when no submission with the specified ID exists.
            SubmissionRegistry.StudyPidMismatchError:
                when the submission does not hold the provided study PID.
        """
        submission = self._submission_store.get_by_id(submission_id)
        held_study_pid = lookup_study_pid(
            anchor=self._study_anchor, accession_map=submission.accession_map
        )
        if held_study_pid != study_pid:
            raise self.StudyPidMismatchError(
                submission_id=submission_id, study_pid=study_pid
            )

    def upsert_submission_content(
        self, *, submission_id: str, content: SubmissionContent
    ) -> None:
        """Insert or update the content of a pending submission.
        The metadata is validated against the model, persisted in the submission store,
        and finally published as source event.

        Raises:
            SubmissionRegistry.SubmissionDoesNotExistError:
                when no submission exists for the specified id.
            SubmissionRegistry.ValidationError:
                when the provided content failed validation against the metadata model.
            SubmissionRegistry.StatusError:
                when the status of the specified submission is not pending.
        """
        submission = self._get_submission_with_status(
            id_=submission_id,
            expected_status=models.SubmissionStatus.PENDING,
        )

        # raises ValidationError if not valid, before any accession is minted:
        self._metadata_validator.validate(content)
        self._metadata_validator.check_aliases_are_ascii(content)
        self._metadata_validator.check_alias_uniqueness(content)

        updated_accession_map = generate_accession_map(
            content=content,
            existing_accession_map=submission.accession_map,
            accession_registry=self._accession_registry,
            anchor_points_by_target=self._anchor_points_by_target,
        )

        updated_submission = submission.model_copy(
            update={"content": content, "accession_map": updated_accession_map}
        )
        self._submission_store.update_existing(submission=updated_submission)

        self._event_publisher.publish_submission(updated_submission)

    def update_submission_header(
        self, *, submission_id: str, header: models.SubmissionHeader
    ) -> None:
        """Replace the title and description of a pending submission. No source event
        is published, since the event does not carry them.

        Raises:
            SubmissionRegistry.SubmissionDoesNotExistError:
                when no submission exists for the specified id.
            SubmissionRegistry.StatusError:
                when the status of the specified submission is not pending.
        """
        submission = self._get_submission_with_status(
            id_=submission_id,
            expected_status=models.SubmissionStatus.PENDING,
        )

        updated_submission = submission.model_copy(update=header.model_dump())
        self._submission_store.update_existing(submission=updated_submission)

    def complete_submission(self, *, id_: str) -> None:
        """Declare an existing submission as complete. The content of the submission
        cannot change anymore afterwards.


        Raises:
            SubmissionRegistry.SubmissionDoesNotExistError:
                when no submission exists for the specified id.
            SubmissionRegistry.StatusError:
                when the status of the specified submission is not pending.
            SubmissionRegistry.ContentEmptyError:
                when the content of the specified sumbission has not yet been specified.
        """
        submission = self._get_submission_with_status(
            id_=id_, expected_status=models.SubmissionStatus.PENDING
        )

        if submission.content is None:
            raise self.ContentEmptyError(submission_id=id_)

        status_change = models.StatusChange(
            timestamp=now_as_utc(), new_status=models.SubmissionStatus.COMPLETED
        )
        updated_submission = submission.model_copy(
            update={
                "status_history": submission.status_history  # noqa: RUF005
                + (status_change,)
            }
        )
        self._submission_store.update_existing(submission=updated_submission)

        self._event_publisher.publish_submission(updated_submission)
