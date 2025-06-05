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

"""Loading schemapack and datapack definitions.

Warning: This is an internal part of the library and might change without notice.
"""

from pathlib import Path

import pydantic

from schemapack._internals.utils import transient_directory_change
from schemapack.exceptions import DataPackSpecError, SchemaPackSpecError
from schemapack.spec.datapack import DataPack
from schemapack.spec.schemapack import SchemaPack
from schemapack.utils import read_json_or_yaml_mapping


def load_schemapack(path: Path):
    """Load a schemapack definition from a file."""
    schemapack_dict = read_json_or_yaml_mapping(path)

    with transient_directory_change(path.parent):
        try:
            return SchemaPack.model_validate(schemapack_dict)
        except pydantic.ValidationError as error:
            raise SchemaPackSpecError(
                message=str(error), details=error.errors()
            ) from error


def load_datapack(path: Path):
    """Load a datapack definition from a file."""
    datapack_dict = read_json_or_yaml_mapping(path)

    try:
        return DataPack.model_validate(datapack_dict)
    except pydantic.ValidationError as error:
        raise DataPackSpecError(message=str(error), details=error.errors()) from error
