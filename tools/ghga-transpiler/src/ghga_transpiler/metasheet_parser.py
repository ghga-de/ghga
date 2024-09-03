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

"""Helper functions to parse the configuration sheets in a workbook"""

from collections import defaultdict

from openpyxl import Workbook
from pydantic import BaseModel, Field

from .config import WorkbookConfig
from .exceptions import MetaColumnNotFound, MetaColumnNotUnique


class MetaInfo(BaseModel):
    """Class with constants that are required to parse the configuration worksheets
    of a workbook.
    """

    column_meta: str = Field(
        default="__column_meta",
        description="Name of a sheet that"
        + " consists of column settings of the individual"
        + " worksheets in a workbook.",
    )
    sheet_meta: str = Field(
        default="__sheet_meta",
        description="Name of a sheet that"
        + " consists of general settings of individual worksheets"
        + " (e.g. header_row, start_column) in a workbook.",
    )
    name_column: str = Field(
        default="sheet",
        description="The name of the column in"
        + " column_meta and sheet_meta worksheets that holds the"
        + " names of the worksheets in the workbook that the settings"
        + " are applied to.",
    )


def read_meta_information(workbook: Workbook, meta_sheet_name: str):
    """Reads the content of a worksheet"""
    if meta_sheet_name in workbook.sheetnames:
        sheet_meta_header = [cell.value for cell in workbook[meta_sheet_name][1]]
        sheet_meta_values = workbook[meta_sheet_name].iter_rows(
            min_row=2, values_only=True
        )
        return [
            dict(zip(sheet_meta_header, val, strict=True)) for val in sheet_meta_values
        ]
    raise SyntaxError(
        f"Unable to extract the sheet {meta_sheet_name} from the workbook."
    )


def reshape_columns_meta(column_meta: list, name_column: str) -> dict[str, list]:
    """Reshapes column metadata into a dictionary where keys are worksheet
    names and values are lists of column metadata dictionaries. Worksheet names comes
    from the column 'name_column'.
    """
    worksheet_columns: dict[str, list[dict]] = defaultdict(list)
    for item in column_meta:
        try:
            sheet_name = item.get(name_column)
        except KeyError as err:
            raise MetaColumnNotFound(
                f"{name_column} column not found in column meta sheet"
            ) from err
        worksheet_columns[sheet_name].append(item)
    return worksheet_columns


def reshape_settings_meta(settings_meta: list, name_column: str) -> dict[str, dict]:
    """Reshapes settings metadata into a dictionary where keys
    are worksheet names and values are worksheet settings dictionaries.
    Worksheet names comes from the column 'name_column'.
    """
    worksheet_settings: dict = {}
    for item in settings_meta:
        try:
            sheet_name = item.get(name_column)
        except KeyError as err:
            raise MetaColumnNotFound(
                f"{name_column} column not found in settings meta sheet"
            ) from err
        if sheet_name in worksheet_settings:
            raise MetaColumnNotUnique(
                f"Duplicate sheet name {
                    sheet_name} in settings meta column {name_column}"
            )
        worksheet_settings[sheet_name] = item
    return worksheet_settings


def worksheet_meta_information(
    workbook: Workbook, meta_info: MetaInfo = MetaInfo()
) -> dict[str, dict]:
    """Creates a dictionary containing both settings and columns metadata for each worksheet"""
    settings = read_meta_information(workbook, meta_info.sheet_meta)
    columns = read_meta_information(workbook, meta_info.column_meta)
    reshaped_settings = reshape_settings_meta(settings, meta_info.name_column)
    reshaped_columns = reshape_columns_meta(columns, meta_info.name_column)
    return {
        key: {"settings": reshaped_settings[key], "columns": reshaped_columns[key]}
        for key in reshaped_settings
    }


def get_workbook_config(workbook: Workbook) -> WorkbookConfig:
    """Gets workbook configurations from the worksheet __sheet_meta"""
    worksheet_meta = worksheet_meta_information(workbook)
    return WorkbookConfig.model_validate({"worksheets": worksheet_meta})
