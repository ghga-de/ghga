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

"""Dependency dummies for the claims repository used in view definitions.

The dummies are overridden by the actual dependencies when preparing the application.
"""

from typing import Annotated

from fastapi import Depends
from ghga_service_commons.api.di import DependencyDummy

from .ports.dao import ClaimDao

__all__ = ["ClaimDaoDependency", "get_claim_dao"]

get_claim_dao = DependencyDummy("claim_dao")

ClaimDaoDependency = Annotated[ClaimDao, Depends(get_claim_dao)]
