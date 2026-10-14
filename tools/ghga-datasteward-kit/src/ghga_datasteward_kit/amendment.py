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

"""Extend an already accessioned submission with additional metadata.

A second `metadata submit` always creates a new submission with a fresh set of
accessions, which breaks every reference to the files already ingested from the
previous one. Amending instead keeps the accession of every alias that is still
present and mints accessions only for aliases that are new.

Everything here drives metldata through its public API, so that metldata itself needs
no changes.
"""

import logging
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import TypeAlias

import yaml
from pydantic import BaseModel, Field

from ghga_datasteward_kit.exceptions import AmendmentAbortedError, AmendmentStatusError
from ghga_datasteward_kit.metadata import MetadataConfig
from ghga_datasteward_kit.utils import load_config_yaml
from metldata.accession_registry.accession_registry import AccessionRegistry
from metldata.accession_registry.accession_store import AccessionStore
from metldata.custom_types import Json
from metldata.event_handling.event_handling import FileSystemEventPublisher
from metldata.model_utils.anchors import get_anchors_points_by_target
from metldata.model_utils.metadata_validator import MetadataValidator
from metldata.submission_registry.event_publisher import SourceEventPublisher
from metldata.submission_registry.identifiers import (
    generate_accession_map,
    get_aliases_for_resources,
)
from metldata.submission_registry.models import Submission, SubmissionStatus
from metldata.submission_registry.submission_store import SubmissionStore


AccessionMap: TypeAlias = dict[str, dict[str, str]]

PREVIEW_LIMIT = 20


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


class AccessionDiff(BaseModel):
    """The effect an applied amendment had on the accessions of a submission."""

    preserved: AccessionMap = Field(default_factory=dict)
    minted: AccessionMap = Field(default_factory=dict)
    dropped: AccessionMap = Field(default_factory=dict)

    @property
    def preserved_count(self) -> int:
        """The number of preserved accessions."""
        return _count_accessions(accession_map=self.preserved)

    @property
    def minted_count(self) -> int:
        """The number of newly minted accessions."""
        return _count_accessions(accession_map=self.minted)

    @property
    def dropped_count(self) -> int:
        """The number of dropped accessions."""
        return _count_accessions(accession_map=self.dropped)


ConfirmCallback = Callable[[AccessionChanges], bool]


def plan_accession_changes(
    *,
    content: Json,
    existing_accession_map: AccessionMap,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> AccessionChanges:
    """Work out which accessions an amendment would keep, drop, and mint, without
    minting anything.

    Mirrors how `generate_accession_map` decides, so the preview matches what applying
    the amendment actually does.
    """
    preserved: AccessionMap = {}
    new_aliases: dict[str, list[str]] = {}

    for anchor, resources in content.items():
        accessions_for_anchor = existing_accession_map.get(anchor, {})

        for alias in get_aliases_for_resources(
            resources=resources,
            root_slot=anchor,
            anchor_points_by_target=anchor_points_by_target,
        ):
            accession = accessions_for_anchor.get(alias)
            if accession:
                preserved.setdefault(anchor, {})[alias] = accession
            else:
                new_aliases.setdefault(anchor, []).append(alias)

    dropped: AccessionMap = {}
    for anchor, accessions_for_anchor in existing_accession_map.items():
        preserved_for_anchor = preserved.get(anchor, {})
        for alias, accession in accessions_for_anchor.items():
            if alias not in preserved_for_anchor:
                dropped.setdefault(anchor, {})[alias] = accession

    return AccessionChanges(
        preserved=preserved, dropped=dropped, new_aliases=new_aliases
    )


def diff_accession_maps(*, before: AccessionMap, after: AccessionMap) -> AccessionDiff:
    """Compare the accession maps from before and after an amendment.

    An alias whose accession changed is reported as both dropped and minted, so that a
    change can never hide as a preservation.
    """
    preserved: AccessionMap = {}
    minted: AccessionMap = {}
    dropped: AccessionMap = {}

    for anchor in before.keys() | after.keys():
        accessions_before = before.get(anchor, {})
        accessions_after = after.get(anchor, {})

        for alias, accession in accessions_after.items():
            if accessions_before.get(alias) == accession:
                preserved.setdefault(anchor, {})[alias] = accession
            else:
                minted.setdefault(anchor, {})[alias] = accession

        for alias, accession in accessions_before.items():
            if accessions_after.get(alias) != accession:
                dropped.setdefault(anchor, {})[alias] = accession

    return AccessionDiff(preserved=preserved, minted=minted, dropped=dropped)


def needs_confirmation(*, changes: AccessionChanges) -> bool:
    """Whether an amendment is risky enough to require explicit confirmation.

    Dropping accessions is risky because a later load removes the corresponding
    resources from the running system. Preserving none at all is risky because it
    usually means the wrong submission or the wrong aliases.
    """
    return changes.dropped_count > 0 or changes.preserved_count == 0


def _format_resource_lines(
    *, resources: Mapping[str, Iterable[str]], limit: int | None = None
) -> list[str]:
    """Render anchor and alias pairs as indented lines, optionally truncated."""
    lines = [
        f"    {anchor} / {alias}"
        for anchor in sorted(resources)
        for alias in sorted(resources[anchor])
    ]

    if limit is not None and len(lines) > limit:
        omitted = len(lines) - limit
        lines = [*lines[:limit], f"    ... and {omitted} more"]

    return lines


def format_amendment_report(
    *,
    submission_id: str,
    changes: AccessionChanges,
    preview_limit: int | None = PREVIEW_LIMIT,
) -> str:
    """Describe what an amendment would do, for the steward to confirm."""
    lines = [
        f"Submission {submission_id}",
        "",
        f"  preserved {changes.preserved_count:>6} accessions (unchanged)",
        f"  new       {changes.new_alias_count:>6} accessions (to be minted)",
        f"  dropped   {changes.dropped_count:>6} accessions",
    ]

    if changes.new_aliases:
        lines += ["", "New resources:"]
        lines += _format_resource_lines(
            resources=changes.new_aliases, limit=preview_limit
        )

    if changes.dropped:
        lines += [
            "",
            "Dropped resources. Their accessions are released, and the next load"
            " removes",
            "these resources from the running system:",
        ]
        # never truncated: every dropped accession matters
        lines += [
            f"    {anchor} / {alias}  {accession}"
            for anchor in sorted(changes.dropped)
            for alias, accession in sorted(changes.dropped[anchor].items())
        ]

    if changes.preserved_count == 0:
        lines += [
            "",
            "No existing accession applies to this content. Check that the submission"
            " ID",
            "and the aliases in the metadata are the ones you meant.",
        ]

    return "\n".join(lines)


def format_amendment_result(*, diff: AccessionDiff) -> str:
    """Describe the accessions an applied amendment minted."""
    lines = [
        f"Amended. {diff.preserved_count} accessions preserved,"
        f" {diff.minted_count} minted, {diff.dropped_count} dropped."
    ]

    if diff.minted:
        lines += ["", "Minted accessions:"]
        lines += [
            f"    {anchor} / {alias}  {accession}"
            for anchor in sorted(diff.minted)
            for alias, accession in sorted(diff.minted[anchor].items())
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


def amend_metadata(
    *,
    submission_id: str,
    metadata: Json,
    config: MetadataConfig,
    confirm: ConfirmCallback | None = None,
) -> AccessionDiff:
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
        MetadataValidator.ValidationError:
            when the provided metadata failed validation against the metadata model.
        AmendmentAbortedError:
            when the confirm callback declined.
    """
    submission_store = SubmissionStore(config=config)
    accession_registry = AccessionRegistry(
        config=config, accession_store=AccessionStore(config=config)
    )
    source_event_publisher = SourceEventPublisher(
        config=config, provider=FileSystemEventPublisher(config=config)
    )
    anchor_points_by_target = get_anchors_points_by_target(model=config.metadata_model)

    submission = _get_completed_submission(
        submission_store=submission_store, submission_id=submission_id
    )

    # raises ValidationError if not valid, before anything is written:
    MetadataValidator(model=config.metadata_model).validate(metadata)

    changes = plan_accession_changes(
        content=metadata,
        existing_accession_map=submission.accession_map,
        anchor_points_by_target=anchor_points_by_target,
    )

    if confirm is not None and not confirm(changes):
        raise AmendmentAbortedError()

    updated_accession_map = generate_accession_map(
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

    return diff_accession_maps(
        before=submission.accession_map, after=updated_accession_map
    )


def amend_metadata_from_path(
    *,
    submission_id: str,
    metadata_path: Path,
    config_path: Path,
    confirm: ConfirmCallback | None = None,
) -> AccessionDiff:
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
