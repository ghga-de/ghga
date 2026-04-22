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

"""Defines the main GHGA Registry Service inbound port."""

from abc import ABC, abstractmethod

from rs.ports.inbound.rdub_manager import RDUBManagerPort


class GHGARegistryPort(ABC):
    """Inbound port defining all operations of the GHGA Registry Service."""

    @property
    @abstractmethod
    def rdub_manager(self) -> RDUBManagerPort:
        """The RDUBManager component."""
        ...
