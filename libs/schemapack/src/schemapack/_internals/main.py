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

"""High-level convenience functions.

Warning: This is an internal part of the library and might change without notice.
"""

from pathlib import Path

from schemapack._internals.load import load_datapack, load_schemapack
from schemapack._internals.validation import SchemaPackValidator
from schemapack.spec.datapack import DataPack
from schemapack.spec.schemapack import SchemaPack


def load_and_validate(
    *, schemapack_path: Path, datapack_path: Path
) -> tuple[SchemaPack, DataPack]:
    """Load and validate a datapack with respect to a schemapack using the default
    validation plugins.

    Raises:
        schemapack.exceptions.SchemaPackFormatError:
            If the schemapack has an invalid format.
        schemapack.exceptions.DataPackFormatError:
            If the datapack has an invalid format.
        schemapack.exceptions.ValidationError:
            If the datapack is not valid against the schemapack.
    """
    schemapack = load_schemapack(schemapack_path)
    datapack = load_datapack(datapack_path)
    validator = SchemaPackValidator(schemapack=schemapack)
    validator.validate(datapack=datapack)
    return schemapack, datapack
