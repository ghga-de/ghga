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

"""Extend a submission accessioned with flat accessions with additional metadata.

A second `metadata submit` always creates a new submission with a fresh set of
accessions, which breaks every reference to the files already ingested from the
previous one. Amending instead keeps the accession of every alias that is still
present and mints flat accessions, from `legacy_accessioning`, only for aliases that
are new. A submission with study PIDs cannot be amended.

Everything here drives metldata through its public API, so that metldata itself needs
no changes.
"""

import re
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import TypeAlias

import yaml
from pydantic import BaseModel, Field

from ghga_datasteward_kit.amendment.exceptions import (
    AccessionNotLegacyError,
    AmendmentAbortedError,
    AmendmentStatusError,
    StudyAccessionMissingError,
)
from ghga_datasteward_kit.amendment.legacy_accessioning import (
    LEGACY_SUFFIX_LENGTH,
    LegacyAccessionRegistry,
    LegacyAccessionStore,
    check_alias_uniqueness_per_class,
    generate_legacy_accession_map,
)
from ghga_datasteward_kit.metadata import MetadataConfig
from ghga_datasteward_kit.utils import load_config_yaml
from metldata.custom_types import Json
from metldata.event_handling.event_handling import FileSystemEventPublisher
from metldata.model_utils.anchors import (
    AnchorPoint,
    get_anchors_points_by_target,
    lookup_anchor_point,
)
from metldata.model_utils.essentials import MetadataModel
from metldata.model_utils.metadata_validator import MetadataValidator
from metldata.submission_registry.event_publisher import SourceEventPublisher
from metldata.submission_registry.models import Submission, SubmissionStatus
from metldata.submission_registry.submission_store import SubmissionStore

AccessionMap: TypeAlias = dict[str, dict[str, str]]

PREVIEW_LIMIT = 20

# the classes an amendment reports to the data steward: the files, whose accessions
# must not change; the study keeps its accession even under a new alias
AMENDMENT_CLASS_NAMES = (
    "ResearchDataFile",
    "ProcessDataFile",
    "ExperimentMethodSupportingFile",
    "AnalysisMethodSupportingFile",
    "IndividualSupportingFile",
)


def _count_accessions(*, accession_map: AccessionMap) -> int:
    """Count the accessions across all classes of an accession map."""
    return sum(len(accessions) for accessions in accession_map.values())


class AccessionChanges(BaseModel):
    """The accession changes an amendment would cause.

    Computed without minting anything, so it can be shown to a user for confirmation
    before the amendment is applied.
    """

    preserved: AccessionMap = Field(
        default_factory=dict,
        description=(
            "Accessions that are already assigned and would still apply, because their"
            + " alias is still present in the submission content."
        ),
    )

    dropped: AccessionMap = Field(
        default_factory=dict,
        description=(
            "Accessions that would no longer be assigned, because their alias is absent"
            + " from the submission content. These accessions may already be in use"
            + " elsewhere in the system and are never re-assigned."
        ),
    )

    new_aliases: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Aliases that would receive a freshly minted accession, by anchor. The"
            + " accessions themselves are not known until the amendment is applied."
        ),
    )

    @property
    def is_lossless(self) -> bool:
        """Whether applying the amendment would drop no accessions at all."""
        return self.dropped_count == 0

    @property
    def preserved_count(self) -> int:
        """The number of accessions that would be preserved."""
        return _count_accessions(accession_map=self.preserved)

    @property
    def dropped_count(self) -> int:
        """The number of accessions that would be dropped."""
        return _count_accessions(accession_map=self.dropped)

    @property
    def new_alias_count(self) -> int:
        """The number of aliases that would receive a new accession."""
        return sum(len(aliases) for aliases in self.new_aliases.values())


ConfirmCallback = Callable[[AccessionChanges], bool]


def find_class_accession_changes(
    *,
    content: Json,
    existing_accession_map: AccessionMap,
    anchor_points_by_target: dict[str, AnchorPoint],
    class_name: str,
) -> tuple[AccessionMap, AccessionMap, dict[str, list[str]]]:
    """Compare the aliases of one class in the new metadata (`content`) with the
    stored submission's accession map, without minting anything: an alias in both
    keeps its accession, one only in `content` is new, one only in the map is dropped.

    Expects validated content with aliases unique within their class.

    Raises:
        AnchorPointNotFoundError: if the model has no class of the given name.
    """
    anchor_point = lookup_anchor_point(
        class_name=class_name, anchor_points_by_target=anchor_points_by_target
    )

    existing_accessions = existing_accession_map.get(anchor_point.root_slot, {})

    new_class_resources = content.get(
        anchor_point.root_slot, []
    )  # validator checks that root slots exists, hence this does not suppress a key error

    aliases = [
        resource[anchor_point.identifier_slot] for resource in new_class_resources
    ]

    preserved = {
        alias: existing_accessions[alias]
        for alias in aliases
        if alias in existing_accessions
    }

    new_aliases = [alias for alias in aliases if alias not in existing_accessions]

    dropped = {
        alias: accession
        for alias, accession in existing_accessions.items()
        if alias not in preserved
    }

    # an empty group gets no entry, so the class does not show up in it
    root_slot = anchor_point.root_slot
    return (
        {root_slot: preserved} if preserved else {},
        {root_slot: dropped} if dropped else {},
        {root_slot: new_aliases} if new_aliases else {},
    )


def find_accession_changes(
    *,
    content: Json,
    existing_accession_map: AccessionMap,
    anchor_points_by_target: dict[str, AnchorPoint],
    class_names: Iterable[str] = AMENDMENT_CLASS_NAMES,
) -> AccessionChanges:
    """Compare the aliases of the given classes in the new metadata (`content`) with
    the stored submission's accession map, class by class, without minting anything.

    Raises:
        AnchorPointNotFoundError: if the model has no class of one of the given names.
    """
    preserved: AccessionMap = {}
    dropped: AccessionMap = {}
    new_aliases: dict[str, list[str]] = {}

    for class_name in class_names:
        class_preserved, class_dropped, class_new_aliases = (
            find_class_accession_changes(
                content=content,
                existing_accession_map=existing_accession_map,
                anchor_points_by_target=anchor_points_by_target,
                class_name=class_name,
            )
        )
        preserved |= class_preserved
        dropped |= class_dropped
        new_aliases |= class_new_aliases

    return AccessionChanges(
        preserved=preserved, dropped=dropped, new_aliases=new_aliases
    )


def needs_confirmation(*, changes: AccessionChanges) -> bool:
    """Whether an amendment is risky enough to require explicit confirmation.

    Dropping accessions is risky because a later load removes the corresponding
    resources from the running system. Preserving none at all is risky because it
    usually means the wrong submission or the wrong aliases.
    """
    return changes.dropped_count > 0 or changes.preserved_count == 0


def _truncate(lines: list[str], *, limit: int | None) -> list[str]:
    """Cut the lines at the limit, saying how many were left out."""
    if limit is None or len(lines) <= limit:
        return lines

    return [*lines[:limit], f"    ... and {len(lines) - limit} more"]


def format_amendment_report(
    *,
    submission_id: str,
    changes: AccessionChanges,
    preview_limit: int | None = PREVIEW_LIMIT,
) -> str:
    """Describe the changes `find_accession_changes` found, for the data steward to
    confirm: the dropped, new and kept files, each with its count and aliases, the
    aliases cut at `preview_limit`.
    """
    dropped_lines = [
        f"    {root_slot} / {alias}  {accession}"
        for root_slot in sorted(changes.dropped)
        for alias, accession in sorted(changes.dropped[root_slot].items())
    ]
    new_lines = [
        f"    {root_slot} / {alias}"
        for root_slot in sorted(changes.new_aliases)
        for alias in sorted(changes.new_aliases[root_slot])
    ]
    kept_lines = [
        f"    {root_slot} / {alias}  {accession}"
        for root_slot in sorted(changes.preserved)
        for alias, accession in sorted(changes.preserved[root_slot].items())
    ]

    lines = [f"Submission {submission_id}"]
    if dropped_lines:
        lines += [
            "",
            f"Dropped files ({changes.dropped_count}). Their accessions are never given"
            " out again, and the next load removes these files from the running"
            " system:",
            *_truncate(dropped_lines, limit=preview_limit),
        ]
    if new_lines:
        lines += [
            "",
            f"New files ({changes.new_alias_count}):",
            *_truncate(new_lines, limit=preview_limit),
        ]
    if kept_lines:
        lines += [
            "",
            f"Kept files ({changes.preserved_count}):",
            *_truncate(kept_lines, limit=preview_limit),
        ]
    else:
        lines += [
            "",
            "No existing alias is kept. Check that the submission ID and the aliases"
            " in the metadata are the ones you meant.",
        ]

    return "\n".join(lines)


def _get_completed_submission(
    *, submission_store: SubmissionStore, submission_id: str
) -> Submission:
    """Get a submission that an amendment may be applied to.

    Raises:
        SubmissionStore.SubmissionDoesNotExistError:
            when no submission exists for the specified id.
        AmendmentStatusError:
            when the stored submission is not completed.
    """
    submission = submission_store.get_by_id(submission_id=submission_id)

    if submission.current_status != SubmissionStatus.COMPLETED:
        raise AmendmentStatusError(
            submission_id=submission_id,
            current_status=submission.current_status.value,
        )

    return submission


def is_legacy_study_accession(*, study_accession: str) -> bool:
    """Tell whether the accession is a flat one: 'GHGA', one letter, 14 digits."""
    return bool(
        re.fullmatch(rf"GHGA[A-Z][0-9]{{{LEGACY_SUFFIX_LENGTH}}}", study_accession)
    )


def _check_legacy_study_accession(
    *,
    submission: Submission,
    study_class_name: str,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> None:
    """Check that a stored submission has a study accession and that it is a flat one,
    since only a submission accessioned before study PIDs can be amended.

    Raises:
        StudyAccessionMissingError:
            when the stored accession map holds no study accession.
        AccessionNotLegacyError:
            when the study accession is not a flat one.
    """
    study_anchor = anchor_points_by_target[study_class_name].root_slot
    study_accession = next(
        iter(submission.accession_map.get(study_anchor, {}).values()), None
    )
    if study_accession is None:
        raise StudyAccessionMissingError(submission_id=submission.id)
    if not is_legacy_study_accession(study_accession=study_accession):
        raise AccessionNotLegacyError(
            submission_id=submission.id, study_accession=study_accession
        )


def _validate_amended_metadata(
    *,
    metadata: Json,
    model: MetadataModel,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> None:
    """Validate the new metadata against the model, which allows exactly one study,
    and check that no alias is repeated within a class.

    Raises:
        MetadataValidator.ValidationError:
            when the metadata failed validation or an alias is repeated in its class.
    """
    MetadataValidator(model=model).validate(metadata)
    # a flat accession holds no alias, so only a repeat within a class matters
    check_alias_uniqueness_per_class(
        content=metadata, anchor_points_by_target=anchor_points_by_target
    )


def amend_metadata(
    *,
    submission_id: str,
    metadata: Json,
    config: MetadataConfig,
    confirm: ConfirmCallback | None = None,
) -> None:
    """Replace the content of a completed submission, keeping the accession of every
    alias that is still present and minting accessions only for new aliases.

    The submission keeps its ID and its completed status, so the republished source
    event replaces the previous one instead of adding a second submission.

    The confirm callback is handed the planned changes before anything is written, so
    it can report them and decide whether to go ahead. Returning False aborts.
    Use `needs_confirmation` to decide when a prompt is warranted.

    Raises:
        SubmissionStore.SubmissionDoesNotExistError:
            when no submission exists for the specified id.
        AmendmentStatusError:
            when the stored submission is not completed.
        StudyAccessionMissingError:
            when the stored accession map holds no study accession.
        AccessionNotLegacyError:
            when the study accession of the stored submission is not a flat one.
        MetadataValidator.ValidationError:
            when the provided metadata failed validation against the metadata model
            or the alias checks.
        AmendmentAbortedError:
            when the confirm callback declined.
    """
    submission_store = SubmissionStore(config=config)
    submission = _get_completed_submission(
        submission_store=submission_store, submission_id=submission_id
    )

    # loaded once: every access to `config.metadata_model` reads the model file again
    model = config.metadata_model
    anchor_points_by_target = get_anchors_points_by_target(model=model)

    _check_legacy_study_accession(
        submission=submission,
        study_class_name=config.study_class_name,
        anchor_points_by_target=anchor_points_by_target,
    )
    _validate_amended_metadata(
        metadata=metadata, model=model, anchor_points_by_target=anchor_points_by_target
    )

    source_event_publisher = SourceEventPublisher(
        config=config, provider=FileSystemEventPublisher(config=config)
    )

    accession_registry = LegacyAccessionRegistry(
        config=config, accession_store=LegacyAccessionStore(config=config)
    )

    changes = find_accession_changes(
        content=metadata,
        existing_accession_map=submission.accession_map,
        anchor_points_by_target=anchor_points_by_target,
    )

    if confirm is not None and not confirm(changes):
        raise AmendmentAbortedError()

    updated_accession_map = generate_legacy_accession_map(
        content=metadata,
        existing_accession_map=submission.accession_map,
        accession_registry=accession_registry,
        anchor_points_by_target=anchor_points_by_target,
    )

    updated_submission = submission.model_copy(
        update={"content": metadata, "accession_map": updated_accession_map}
    )
    submission_store.update_existing(submission=updated_submission)

    # same submission ID, so this replaces the previous source event rather than
    # adding a second submission for the transformation workflow to pick up
    source_event_publisher.publish_submission(updated_submission)


def amend_metadata_from_path(
    *,
    submission_id: str,
    metadata_path: Path,
    config_path: Path,
    confirm: ConfirmCallback | None = None,
) -> None:
    """Read metadata and config from the specified paths, then amend the specified
    submission.
    """
    with open(metadata_path, encoding="utf8") as metadata_file:
        metadata = yaml.safe_load(metadata_file)

    config = load_config_yaml(path=config_path, config_cls=MetadataConfig)

    return amend_metadata(
        submission_id=submission_id,
        metadata=metadata,
        config=config,
        confirm=confirm,
    )
