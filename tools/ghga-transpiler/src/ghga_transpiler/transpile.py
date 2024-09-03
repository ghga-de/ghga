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
#

"""This module contains functionalities for processing excel sheets into json object."""

from pathlib import Path

from arcticfreeze import FrozenDict
from openpyxl import Workbook
from schemapack.spec.datapack import DataPack

from .config import WorkbookConfig
from .metasheet_parser import get_workbook_config
from .models import GHGAWorkbook
from .transpiler_io import read_workbook
from .workbook_parser import GHGAWorkbookParser


def parse_workbook(workbook: Workbook, config: WorkbookConfig) -> GHGAWorkbook:
    """Converts a workbook into GHGAWorkbook"""
    return GHGAWorkbookParser(config=config, workbook=workbook).parse()


def transpile_to_datapack(workbook: GHGAWorkbook) -> DataPack:
    """Convert GHAWorkbook into a Datapack instance."""
    return DataPack(
        datapack="0.3.0", resources=FrozenDict(workbook.model_dump()), rootResource=None
    )


def transpile(spread_sheet: Path) -> DataPack:
    """The main flow with the steps to transpile a spreadsheet into a datapack."""
    workbook = read_workbook(spread_sheet)
    workbook_config = get_workbook_config(workbook)
    ghga_workbook = parse_workbook(workbook, workbook_config)
    ghga_datapack = transpile_to_datapack(ghga_workbook)
    return ghga_datapack
