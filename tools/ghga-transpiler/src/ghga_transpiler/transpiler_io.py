# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
#
#

"""IO related functionality"""

from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook
from schemapack import dumps_datapack
from schemapack.spec.datapack import DataPack

from .exceptions import WorkbookNotFound


def read_workbook(path: Path) -> Workbook:
    """Function to read-in a workbook"""
    try:
        return load_workbook(path)
    except FileNotFoundError as err:
        raise WorkbookNotFound(f"Spreadsheet file not found on {path}") from err


def write_datapack(
    data: DataPack, path: Path | None, yaml_format: bool, force: bool
) -> None:
    """Writes data as JSON to the specified output path or
    to stdout if the path is None, or overwrites an existing output file if
    'force' is True.
    """
    datapack = dumps_datapack(data, yaml_format=yaml_format)
    if path is None:
        sys.stdout.write(datapack)
    elif path.exists() and not force:
        raise FileExistsError(f"File already exists: {path}")
    else:
        with open(file=path, mode="w", encoding="utf8") as outfile:
            outfile.write(datapack)
