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

"""Core functionality of the reverse transpiler service."""

from rts.config import Config
from rts.ports.inbound.rev_tran import ReverseTranspilerPort
from rts.ports.outbound.dao import MetadataDao


class ReverseTranspiler(ReverseTranspilerPort):
    """Provides functionality to convert JSON files to XLSX format.

    Included conversion logic contains specific transformations for GHGA metadata.
    """

    def __init__(self, config: Config, dao: MetadataDao):
        self._config = config

    async def json_to_xlsx(
        self,
        input_file: str,
        output_file: str | None = None,
    ) -> bytes:
        """Convert a JSON file to an XLSX file.

        Args:
        - `input_file`: Path to the input JSON file
        - `output_file`: Path to the output XLSX file. If not provided,
                                    it will use the input filename with .xlsx extension.

        Returns content of the generated XLSX file as bytes.
        """
        raise NotImplementedError()
