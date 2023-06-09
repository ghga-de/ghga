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

from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Generator

import pytest

from metldata.config import SubmissionConfig
from tests.fixtures.metadata_models import VALID_MINIMAL_MODEL_EXAMPLE_PATH

PREFIX_MAPPING = {
    "File": "GHGAF",
    "Experiment": "GHGAE",
    "Sample": "GHGAS",
    "Dataset": "GHGAD",
}


@pytest.fixture
def config_sub_fixture() -> Generator[SubmissionConfig, None, None]:
    """Generate a test config."""

    with TemporaryDirectory() as submission_store_dir:
        with NamedTemporaryFile() as accession_store_path:
            yield SubmissionConfig(
                metadata_model_path=VALID_MINIMAL_MODEL_EXAMPLE_PATH,
                submission_store_dir=submission_store_dir,
                accession_store_path=accession_store_path.name,
                prefix_mapping=PREFIX_MAPPING,
            )
