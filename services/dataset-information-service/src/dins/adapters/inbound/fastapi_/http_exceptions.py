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

"""A collextion of http exceptions."""

from ghga_service_commons.httpyexpect.server import HttpCustomExceptionBase
from pydantic import BaseModel


class HttpDatasetNotFoundError(HttpCustomExceptionBase):
    """Raised when a file with given ID could not be found."""

    exception_id = "datasetNotFound"

    class DataModel(BaseModel):
        """Model for exception data"""

        dataset_id: str

    def __init__(self, *, dataset_id: str, status_code: int = 404):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=f"Information for the dataset with ID {dataset_id} is not registered.",
            data={"dataset_id": dataset_id},
        )


class HttpInformationNotFoundError(HttpCustomExceptionBase):
    """Raised when a file with given ID could not be found."""

    exception_id = "informationNotFound"

    class DataModel(BaseModel):
        """Model for exception data"""

        accession: str

    def __init__(self, *, accession: str, status_code: int = 404):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=(
                f"Information for the file with accession {accession} is not registered."
            ),
            data={"accession": accession},
        )
