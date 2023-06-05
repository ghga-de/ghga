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

"""Test data"""

from pathlib import Path
from typing import Dict, List

from hexkit.providers.s3.testutils import TEST_FILE_PATHS, FileObject


class FileState:
    """_
    File State class for available files
    """

    def __init__(
        self,
        *,
        file_id: str,
        grouping_label: str,
        file_path: Path,
        populate_storage: bool = True,
    ):
        """
        Initialize file state and create imputed attributes.
        Set populate_storage to true in order to upload them to the localstack storage
        """
        self.file_id = file_id
        self.grouping_label = grouping_label
        self.file_path = file_path
        self.populate_storage = populate_storage

        self.storage_objects: List[FileObject] = []
        if self.populate_storage:
            self.storage_objects.append(
                FileObject(
                    file_path=self.file_path,
                    bucket_id=self.grouping_label,
                    object_id=self.file_id,
                )
            )


FILES: Dict[str, FileState] = {
    "encrypted_file": FileState(
        file_id="encrypted",
        grouping_label="inbox",
        file_path=TEST_FILE_PATHS[0],
        populate_storage=False,
    ),
    "file_uploadable": FileState(
        file_id="uploadable",
        grouping_label="inbox",
        file_path=TEST_FILE_PATHS[0],
        populate_storage=False,
    ),
    "file_not_uploadable": FileState(
        file_id="not-uploadable",
        grouping_label="inbox",
        file_path=TEST_FILE_PATHS[1],
        populate_storage=False,
    ),
    "file_with_bad_path": FileState(
        file_id="bad-path",
        grouping_label="inbox",
        file_path=Path("/bad/path.xyz"),
        populate_storage=False,
    ),
    "file_uploaded": FileState(
        file_id="uploaded",
        grouping_label="inbox",
        file_path=TEST_FILE_PATHS[2],
        populate_storage=True,
    ),
    "file_downloadable": FileState(
        file_id="downloadable",
        grouping_label="outbox",
        file_path=TEST_FILE_PATHS[3],
        populate_storage=True,
    ),
    "file_envelope_missing": FileState(
        file_id="envelope-missing",
        grouping_label="outbox",
        file_path=TEST_FILE_PATHS[3],
        populate_storage=True,
    ),
    "file_not_downloadable": FileState(
        file_id="not-downloadable",
        grouping_label="outbox",
        file_path=TEST_FILE_PATHS[1],
        populate_storage=False,
    ),
    "file_retry": FileState(
        file_id="retry",
        grouping_label="outbox",
        file_path=TEST_FILE_PATHS[1],
        populate_storage=False,
    ),
}
