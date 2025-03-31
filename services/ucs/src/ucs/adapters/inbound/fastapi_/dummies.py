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
#

"""A collection of dependency dummies that are used in view definitions but need to be
replaced at runtime by actual dependencies.
"""

from typing import Annotated

from fastapi import Depends
from ghga_service_commons.api.di import DependencyDummy

from ucs.ports.inbound.file_service import FileMetadataServicePort
from ucs.ports.inbound.upload_service import UploadServicePort

upload_service_port = DependencyDummy("upload_service_port")
file_metadata_service_port = DependencyDummy("file_metadata_service_port")

UploadServiceDummy = Annotated[UploadServicePort, Depends(upload_service_port)]
FileMetadataServiceDummy = Annotated[
    FileMetadataServicePort, Depends(file_metadata_service_port)
]
