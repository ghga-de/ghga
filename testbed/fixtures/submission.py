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

""" Metadata related  fixture """

import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator

from pydantic import BaseSettings
from pytest import fixture

BASE_DIR = Path(__file__).parent.parent
TMP_DIR = Path(tempfile.gettempdir())


class SubmissionConfig(BaseSettings):
    """Config for metadata and related submissions"""

    submission_registry: Path = TMP_DIR / "submission"
    event_store: Path = submission_registry / "event_store"
    submission_store: Path = submission_registry / "submission_store"
    accession_store: Path = submission_registry / "accession_store"
    embedded_public_event: Path = event_store / "artifact.embedded_public"

    metadata_config_path: Path = (
        BASE_DIR / "example_data" / "metadata" / "metadata_config.yaml"
    )
    metadata_model_path: Path = (
        BASE_DIR / "example_data" / "metadata" / "metadata_model.yaml"
    )
    metadata_path: Path = BASE_DIR / "example_data" / "metadata" / "metadata.json"
    metadata_model_file: str = "metadata_model.yaml"
    metadata_file_fields: list = [
        "analysis_process_output_files",
        "sample_files",
        "sequencing_process_files",
        "study_files",
    ]

    file_metadata_dir: Path = submission_registry / "file_metadata"


class SubmissionFixture:
    """Submission fixture"""

    config: SubmissionConfig

    def __init__(self, config: SubmissionConfig):
        self.config = config

    def reset_workdir(self):
        submission_registry_path = self.config.submission_registry

        if os.path.exists(submission_registry_path):
            shutil.rmtree(submission_registry_path)

        submission_registry_path.mkdir()
        self.config.event_store.mkdir()
        self.config.submission_store.mkdir()
        self.config.accession_store.touch()

        shutil.copyfile(
            self.config.metadata_model_path,
            submission_registry_path / self.config.metadata_model_file,
        )


@fixture(name="submission")
def submission_fixture() -> Generator[SubmissionFixture, None, None]:
    """Pytest fixture for tests depending on the S3ObjectStorage."""
    config = SubmissionConfig()
    yield SubmissionFixture(config=config)
