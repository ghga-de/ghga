# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from typing import Any

from ghga_service_chassis_lib.utils import now_as_utc

from metldata.submission_registry import models
from metldata.submission_registry.event_publisher import EventPublisher
from metldata.submission_registry.metadata_validator import MetadataValidator
from metldata.submission_registry.submission_store import SubmissionStore


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
                f"The submission with id '{submission_id} has the status"
                + f" '{current_status}' but expected '{expected_status}'."
            )
            super().__init__(message)

    class ContentEmptyError(RuntimeError):
        """Raised when the content of a submission is empty.."""

        def __init__(self, *, submission_id: str):
            message = (
                f"The content for the submission with id '{submission_id} has not yet"
                + " been specified."
            )
            super().__init__(message)

    def __init__(
        self,
        *,
        submission_store: SubmissionStore,
        metadata_validator: MetadataValidator,
        event_publisher: EventPublisher,
    ):
        """Initialize with dependencies and config parameters."""

        self._submission_store = submission_store
        self._metadata_validator = metadata_validator
        self._event_publisher = event_publisher

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
                current_status=str(submission.current_status),
                expected_status=str(expected_status),
            )

        return submission

    def init_submission(self, *, header: models.SubmissionHeader) -> str:
        """Initialize a new submission by providing header information. Returns the
        ID of the created submission."""

        submission_creation = models.SubmissionCreation(**header.dict())
        submission = self._submission_store.insert_new(submission=submission_creation)

        return submission.id

    def get_submission(self, *, id_: str) -> models.Submission:
        """Get details on the existing submission with the specified id.

        Raises:
            SubmissionRegistry.SubmissionDoesNotExistError:
                when no submission with the specified ID exists.
        """

        return self._submission_store.get_by_id(id_)

    def upsert_submission_content(
        self, *, submission_id: str, content: dict[str, Any]
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
            id_=submission_id, expected_status=models.SubmissionStatus.PENDING
        )

        # raises ValidationError if not valid:
        self._metadata_validator.validate(content)

        # update the submission object in the store:
        updated_submission = submission.copy(update={"content": content})
        self._submission_store.update_existing(submission=updated_submission)

        # publish updated submission as source event:
        self._event_publisher.publish_submission(updated_submission)

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

        updated_submission = submission.copy()
        updated_submission.status_history.append(
            models.StatusChange(
                timestamp=now_as_utc(), new_status=models.SubmissionStatus.COMPLETED
            )
        )
        self._submission_store.update_existing(submission=updated_submission)

        # publish updated submission as source event:
        self._event_publisher.publish_submission(updated_submission)
