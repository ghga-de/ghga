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

"""Submit metadata as a new submission with flat accessions, for a study that was
promised a flat accession before its metadata arrived.

`metadata submit` mints a study PID and cannot take a given accession. Here the study
gets the accession it was promised and every other resource a new flat one from
`legacy_accessioning`, so the result is a submission like those from before study
PIDs, which can be amended like them.

Like amendment, this drives metldata through its public API, so that metldata itself
needs no changes.
"""

from pathlib import Path

import yaml

from ghga_datasteward_kit.amendment.amendment import is_legacy_study_accession
from ghga_datasteward_kit.amendment.exceptions import (
    StudyAccessionInUseError,
    StudyAccessionNotFlatError,
)
from ghga_datasteward_kit.amendment.legacy_accessioning import (
    LegacyAccessionRegistry,
    LegacyAccessionStore,
    check_alias_uniqueness_per_class,
)
from ghga_datasteward_kit.metadata import MetadataConfig
from ghga_datasteward_kit.utils import load_config_yaml
from ghga_service_commons.utils.utc_dates import now_as_utc
from metldata.custom_types import Json
from metldata.event_handling.event_handling import FileSystemEventPublisher
from metldata.metadata_utils import lookup_self_id
from metldata.model_utils.anchors import (
    get_anchors_points_by_target,
    lookup_anchor_point,
)
from metldata.model_utils.metadata_validator import MetadataValidator
from metldata.submission_registry.event_publisher import SourceEventPublisher
from metldata.submission_registry.identifiers import (
    generate_accession_map,
    generate_submission_id,
)
from metldata.submission_registry.models import (
    StatusChange,
    Submission,
    SubmissionStatus,
)
from metldata.submission_registry.submission_store import SubmissionStore


def submit_legacy_metadata(
    *,
    submission_title: str,
    submission_description: str,
    study_accession: str,
    metadata: Json,
    config: MetadataConfig,
) -> str:
    """Store the metadata as a new, completed submission whose study has the given
    flat accession and whose other resources get new flat accessions. Returns the ID
    of the submission.

    The study accession is registered in the accession store only once the metadata
    is validated, the other accessions are minted and the submission is written, so
    a run that was refused or could not write can be repeated with the same
    accession.

    Raises:
        StudyAccessionNotFlatError:
            when the given study accession is not a flat one.
        StudyAccessionInUseError:
            when the given study accession is already in the accession store.
        MetadataValidator.ValidationError:
            when the metadata failed validation against the metadata model or an
            alias is repeated in its class.
        AccessionGenerationError:
            when a class in the metadata has no flat prefix.
    """
    if not is_legacy_study_accession(study_accession=study_accession):
        raise StudyAccessionNotFlatError(study_accession=study_accession)

    accession_store = LegacyAccessionStore(config=config)
    if accession_store.has_legacy(accession=study_accession):
        raise StudyAccessionInUseError(study_accession=study_accession)

    # loaded once: every access to `config.metadata_model` reads the model file again
    model = config.metadata_model
    anchor_points_by_target = get_anchors_points_by_target(model=model)

    MetadataValidator(model=model).validate(metadata)
    # a flat accession holds no alias, so only a repeat within a class matters
    check_alias_uniqueness_per_class(
        content=metadata, anchor_points_by_target=anchor_points_by_target
    )

    study_anchor = lookup_anchor_point(
        class_name=config.study_class_name,
        anchor_points_by_target=anchor_points_by_target,
    )
    # the model allows exactly one study, so the validated metadata holds one
    study_alias = lookup_self_id(
        resource=metadata[study_anchor.root_slot][0],
        identifier_slot=study_anchor.identifier_slot,
    )

    # the study is found in the map and kept; the legacy registry mints the rest and
    # stores every class, so the map is flat throughout
    accession_map = generate_accession_map(
        content=metadata,
        existing_accession_map={study_anchor.root_slot: {study_alias: study_accession}},
        accession_registry=LegacyAccessionRegistry(
            config=config, accession_store=accession_store
        ),
        anchor_points_by_target=anchor_points_by_target,
    )

    # pending, then completed, like a submission that went through `metadata submit`
    submission = Submission(
        id=generate_submission_id(),
        title=submission_title,
        description=submission_description,
        content=metadata,
        accession_map=accession_map,
        status_history=(
            StatusChange(timestamp=now_as_utc(), new_status=SubmissionStatus.PENDING),
            StatusChange(timestamp=now_as_utc(), new_status=SubmissionStatus.COMPLETED),
        ),
    )

    # the submission first: if it cannot be written, the study accession stays free
    # for the next run. Should the publishing fail, `metadata amend` with the same
    # metadata publishes the source event of the stored submission.
    SubmissionStore(config=config).insert_new(submission=submission)
    accession_store.save_legacy(accession=study_accession)
    SourceEventPublisher(
        config=config, provider=FileSystemEventPublisher(config=config)
    ).publish_submission(submission)

    return submission.id


def submit_legacy_metadata_from_path(
    *,
    submission_title: str,
    submission_description: str,
    study_accession: str,
    metadata_path: Path,
    config_path: Path,
) -> str:
    """Read metadata and config from the specified paths, then submit the metadata
    with flat accessions.
    """
    with open(metadata_path, encoding="utf8") as metadata_file:
        metadata = yaml.safe_load(metadata_file)

    config = load_config_yaml(path=config_path, config_cls=MetadataConfig)

    return submit_legacy_metadata(
        submission_title=submission_title,
        submission_description=submission_description,
        study_accession=study_accession,
        metadata=metadata,
        config=config,
    )
