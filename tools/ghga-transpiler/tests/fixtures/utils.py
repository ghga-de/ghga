# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Utils for Fixture handling"""

from pathlib import Path

from openpyxl import Workbook


def get_project_root() -> Path:
    """Function to get project root dir"""
    return Path(__file__).absolute().parent.parent.parent


def create_workbook(*args) -> Workbook:
    """Function to create workbook with sheets"""
    workbook = Workbook()
    for arg in args:
        workbook.create_sheet(arg)
    return workbook
