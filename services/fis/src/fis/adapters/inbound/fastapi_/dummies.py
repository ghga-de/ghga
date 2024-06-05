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
#
"""A collection of dependency dummies that are used in view definitions but need to be
replaced at runtime by actual dependencies.
"""

from typing import Annotated

from fastapi import Depends
from ghga_service_commons.api.di import DependencyDummy

from fis.config import Config
from fis.ports.inbound.ingest import (
    LegacyUploadMetadataProcessorPort,
    UploadMetadataProcessorPort,
)

config_dummy = DependencyDummy("config_dummy")
upload_processor_port = DependencyDummy("upload_processor_port")
legacy_upload_processor = DependencyDummy("legacy_upload_processor")

ConfigDummy = Annotated[Config, Depends(config_dummy)]

UploadProcessorPort = Annotated[
    UploadMetadataProcessorPort, Depends(upload_processor_port)
]

LegacyUploadProcessor = Annotated[
    LegacyUploadMetadataProcessorPort, Depends(legacy_upload_processor)
]
