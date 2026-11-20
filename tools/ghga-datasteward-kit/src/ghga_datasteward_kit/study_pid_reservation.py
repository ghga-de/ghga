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

"""Reserve a study PID before the metadata of a study arrives.

The reservation is a pending submission without content whose accession map holds
the new study PID. `submit_pending` fills it once the metadata arrives.
"""

from pathlib import Path

from ghga_datasteward_kit.metadata import MetadataConfig, build_submission_registry
from ghga_datasteward_kit.utils import load_config_yaml
from metldata.submission_registry.models import SubmissionHeader


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
