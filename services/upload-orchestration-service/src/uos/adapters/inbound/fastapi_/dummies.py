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

"""A collection of dependency dummies.

These dummies are used in path operation definitions, but at runtime they need
to be replaced  with actual dependencies.
"""

from typing import Annotated

from fastapi import Depends
from ghga_service_commons.api.di import DependencyDummy
from ghga_service_commons.auth.context import AuthContextProtocol
from ghga_service_commons.auth.ghga import AuthContext

from uos.ports.inbound.orchestrator import UploadOrchestratorPort

__all__ = [
    "AuthProviderDummy",
    "UploadOrchestratorDummy",
    "auth_provider",
    "upload_orchestrator_port",
]

auth_provider = DependencyDummy("auth_provider")
upload_orchestrator_port = DependencyDummy("upload_orchestrator_port")

AuthProviderDummy = Annotated[AuthContextProtocol[AuthContext], Depends(auth_provider)]
UploadOrchestratorDummy = Annotated[
    UploadOrchestratorPort, Depends(upload_orchestrator_port)
]
