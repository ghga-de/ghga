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

""" Step definitions for metadata submission """

import subprocess  # nosec B404
from pathlib import Path

from fixtures.metadata import SubmissionConfig

from .conftest import TIMEOUT


def test_upload_submission(
    submission_workdir: Path, submission_config: SubmissionConfig
):
    """Test submission via DSKit with configured file object,
       expected to run through without errors

    This test case is not async at the moment because in submit workflow
    asyncio.run() is called by metldata dependency.
    """

    completed_submit = subprocess.run(  # nosec B607, B603
        [
            "ghga-datasteward-kit",
            "metadata",
            "submit",
            "--submission-title",
            "Test Submission",
            "--submission-description",
            "Test Submission Description",
            "--metadata-path",
            submission_config.metadata_path,
            "--config-path",
            submission_config.metadata_config_path,
        ],
        capture_output=True,
        check=True,
        timeout=TIMEOUT * 60,
    )

    assert not completed_submit.stdout
    assert b"ERROR" not in completed_submit.stderr

    assert (submission_workdir / submission_config.submission_store).exists()

    completed_transform = subprocess.run(  # nosec B607, B603
        [
            "ghga-datasteward-kit",
            "metadata",
            "transform",
            "--config-path",
            submission_config.metadata_config_path,
        ],
        capture_output=True,
        check=True,
        timeout=15 * 60,
    )

    assert not completed_transform.stdout
    assert b"ERROR" not in completed_transform.stderr
