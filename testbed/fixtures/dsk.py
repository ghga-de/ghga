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

"""Fixture for using the GHGA connector"""

import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

from pydantic import BaseSettings
from pytest import fixture

BASE_DIR = Path(__file__).parent.parent
TMP_DIR = Path(tempfile.gettempdir())


class DskConfig(BaseSettings):
    """Config for metadata and related submissions"""

    submission_registry: Path = TMP_DIR / "submission"
    event_store: Path = submission_registry / "event_store"
    submission_store: Path = submission_registry / "submission_store"
    accession_store: Path = submission_registry / "accession_store"
    embedded_public_event: Path = event_store / "artifact.embedded_public"

    metadata_dir: Path = BASE_DIR / "example_data" / "metadata"
    metadata_config_path: Path = metadata_dir / "metadata_config.yaml"
    metadata_model_path: Path = metadata_dir / "metadata_model.yaml"
    minimal_metadata_path: Path = metadata_dir / "minimal_metadata.json"
    complete_metadata_path: Path = metadata_dir / "complete_metadata.json"

    metadata_model_file: str = "metadata_model.yaml"
    metadata_file_fields: list = [
        "analysis_process_output_files",
        "sample_files",
        "sequencing_process_files",
        "study_files",
    ]

    file_metadata_dir: Path = submission_registry / "file_metadata"
    files_to_upload_tsv: Path = submission_registry / "files.tsv"


class DskFixture:
    """Data Steward Kit fixture"""

    config: DskConfig

    def __init__(self, config: DskConfig):
        self.config = config

    def reset_work_dir(self):
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
        if os.path.exists(self.config.files_to_upload_tsv):
            os.remove(self.config.files_to_upload_tsv)


@fixture(name="dsk", scope="session")
def dsk_fixture() -> Generator[DskFixture, None, None]:
    """Pytest fixture for tests using the Data Steward Kit."""
    config = DskConfig()
    yield DskFixture(config=config)
