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

from pathlib import Path

from pydantic import BaseSettings
from pytest import fixture

BASE_DIR = Path(__file__).parent.parent


class SubmissionConfig(BaseSettings):
    """Config for metadata and related submissions"""

    metadata_config_path: Path = (
        BASE_DIR / "example_data" / "metadata" / "metadata_config.yaml"
    )
    metadata_model_path: Path = (
        BASE_DIR / "example_data" / "metadata" / "metadata_model.yaml"
    )
    metadata_path: Path = BASE_DIR / "example_data" / "metadata" / "metadata.json"
    event_store: str = "event_store"
    submission_store: str = "submission_store"
    accession_store: str = "accession_store"
    metadata_model_filename: str = "metadata_model.yaml"
    metadata_file_fields: list = [
        "analysis_process_output_files",
        "sample_files",
        "sequencing_process_files",
        "study_files",
    ]


@fixture(name="submission_config")  # pyright: ignore
def submission_config_fixture() -> SubmissionConfig:
    """Get the testbed configuration."""

    return SubmissionConfig()  # pyright: ignore
