# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""A collection of http responses."""

from fastapi.responses import JSONResponse

from dins.core.models import DatasetFileInformation, FileInformation


class HttpDatasetInformationResponse(JSONResponse):
    """Return relevant public information for the requested dataset."""

    response_id = "datasetInformation"

    def __init__(
        self, *, dataset_information: DatasetFileInformation, status_code: int = 200
    ):
        """Construct message and init the response."""
        super().__init__(
            content=dataset_information.model_dump(), status_code=status_code
        )


class HttpFileInformationResponse(JSONResponse):
    """Return relevant public information for the requested file."""

    response_id = "fileInformation"

    def __init__(self, *, file_information: FileInformation, status_code: int = 200):
        """Construct message and init the response."""
        super().__init__(content=file_information.model_dump(), status_code=status_code)
