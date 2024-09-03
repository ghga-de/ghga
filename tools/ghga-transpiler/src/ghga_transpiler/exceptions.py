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

"""Module to collect custom exceptions"""


class DuplicatedName(ValueError):
    """Raised when worksheet names are not unique in the config file"""


class MissingWorkbookContent(KeyError):
    """Raised when any worksheet given in the config yaml does not exist in the spreadsheet"""


class WorkbookNotFound(FileNotFoundError):
    """Raised when path to the workbook file not found on a path."""


class MetaColumnNotFound(KeyError):
    """Raised when the 'sheet' column holding the sheet names on the meta_sheets
    (__column_meta, __sheet_meta) does not exist.
    """


class MetaColumnNotUnique(ValueError):
    """Raised when the 'sheet' column holding the sheet names on the meta_sheets
    (__column_meta, __sheet_meta) is not unique.
    """
