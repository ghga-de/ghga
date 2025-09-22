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

"""DAO translators for accessing the database."""

# for convenience: forward errors that may be thrown by DAO instances:
from abc import ABC, abstractmethod

from hexkit.protocols.dao import Dao, ResourceAlreadyExistsError, ResourceNotFoundError
from hexkit.protocols.daopub import DaoPublisher

from ucs.core import models

__all__ = [
    "FileUploadBoxDao",
    "FileUploadDao",
    "ResourceAlreadyExistsError",
    "ResourceNotFoundError",
    "S3UploadDetailsDao",
    "UploadDaoPublisherFactoryPort",
]

S3UploadDetailsDao = Dao[models.S3UploadDetails]
FileUploadBoxDao = DaoPublisher[models.FileUploadBox]
FileUploadDao = DaoPublisher[models.FileUpload]


class UploadDaoPublisherFactoryPort(ABC):
    """Port that provides a factory for file upload-related data access objects.

    These objects will also publish changes according to the outbox pattern.
    """

    @abstractmethod
    async def get_file_upload_box_dao(self) -> DaoPublisher[models.FileUploadBox]:
        """Construct an outbox DAO for FileUploadBox objects"""

    @abstractmethod
    async def get_file_upload_dao(self) -> DaoPublisher[models.FileUpload]:
        """Construct an outbox DAO for FileUpload objects"""
