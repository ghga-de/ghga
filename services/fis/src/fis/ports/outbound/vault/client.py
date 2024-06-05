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
"""Ports for vault interaction"""

from abc import ABC, abstractmethod


class VaultAdapterPort(ABC):
    """Port for vault adapter"""

    class SecretInsertionError(RuntimeError):
        """Wrapper for errors encountered on secret insertion"""

    @abstractmethod
    def store_secret(self, *, secret: str) -> str:
        """
        Store a secret under a subpath of the given prefix.
        Generates a UUID4 as key, uses it for the subpath and returns it.
        """
