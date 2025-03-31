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

"""Abstract definition of an event publisher class"""

from abc import ABC, abstractmethod

from fis.core import models


class EventPubTranslatorPort(ABC):
    """Abstract definition of an event publisher class"""

    @abstractmethod
    async def publish_file_interrogation_success(
        self, *, upload_metadata: models.UploadMetadataBase, secret_id: str
    ):
        """Publish a file interrogation success event"""
        ...
