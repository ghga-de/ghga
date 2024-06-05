# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""Interface for broadcasting events to other services."""

from abc import ABC, abstractmethod

from fis.core.models import UploadMetadataBase


class EventPublisherPort(ABC):
    """A port through which ingest events are communicated with the file backend services."""

    @abstractmethod
    async def send_file_metadata(
        self,
        *,
        upload_metadata: UploadMetadataBase,
        source_bucket_id: str,
        secret_id: str,
        s3_endpoint_alias: str,
    ):
        """Send FileUploadValidationSuccess event to downstream services"""
