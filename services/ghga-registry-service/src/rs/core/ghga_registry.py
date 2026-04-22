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
"""GHGARegistry implementation"""

from rs.ports.inbound.ghga_registry import GHGARegistryPort
from rs.ports.inbound.rdub_manager import RDUBManagerPort


class GHGARegistry(GHGARegistryPort):
    """Top-level class linking all constituent registry operations"""

    def __init__(
        self,
        *,
        rdub_manager: RDUBManagerPort,
    ) -> None:
        self._rdub_manager = rdub_manager

    @property
    def rdub_manager(self) -> RDUBManagerPort:
        """The RDUBManager component."""
        return self._rdub_manager
