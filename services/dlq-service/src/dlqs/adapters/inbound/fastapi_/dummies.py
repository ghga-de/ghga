# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Dependency dummies for the FastAPI endpoints"""

from typing import Annotated

from fastapi import Depends
from ghga_service_commons.api.di import DependencyDummy

from dlqs.config import Config
from dlqs.ports.inbound.dlq_manager import DLQManagerPort

config_dummy = DependencyDummy("config_dummy")
dlq_manager_port = DependencyDummy("dlq_manager_port")

ConfigDummy = Annotated[Config, Depends(config_dummy)]
DLQManagerDummy = Annotated[DLQManagerPort, Depends(dlq_manager_port)]
