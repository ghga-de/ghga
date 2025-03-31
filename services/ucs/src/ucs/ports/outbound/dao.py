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

from dataclasses import dataclass

# for convenience: forward errors that may be thrown by DAO instances:
from hexkit.protocols.dao import (
    Dao,
    ResourceAlreadyExistsError,  # noqa: F401
    ResourceNotFoundError,  # noqa: F401
)

from ucs.core import models


@dataclass
class DaoCollectionPort:
    """A collection of DAOs for interacting with the database."""

    file_metadata: Dao[models.FileMetadata]
    upload_attempts: Dao[models.UploadAttempt]
