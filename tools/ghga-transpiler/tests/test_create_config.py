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

"""Tests for creating the config"""

from ghga_transpiler.config.config import (
    Config,
    DefaultSettings,
    Worksheet,
    WorksheetSettings,
)


def test_config_params() -> None:
    """Testing if default parameters of config yaml are used in the absence of worksheet settings"""
    books_sheet = Worksheet(
        sheet_name="books", settings=WorksheetSettings(name="books", end_column=3)
    )
    publisher_sheet = Worksheet(
        sheet_name="publisher", settings=WorksheetSettings(name="publisher")
    )

    config = Config(
        default_settings=DefaultSettings(start_row=1, start_column=1, end_column=2),
        worksheets=[books_sheet, publisher_sheet],
        ghga_metadata_version="0.0.0",
    )
    assert config.worksheets[1].settings is not None  # nosec
    assert config.worksheets[1].settings.end_column == 2
