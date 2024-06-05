# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""FastAPI dependencies (used with the `Depends` feature)"""

from fastapi import Depends

from ekss.adapters.outbound.vault import VaultAdapter
from ekss.config import CONFIG, VaultConfig


def config_injector():
    """Injectable config, overridable for tests"""
    return CONFIG


def get_vault(config: VaultConfig = Depends(config_injector)) -> VaultAdapter:
    """Get VaultAdapter for config"""
    return VaultAdapter(config=config)
