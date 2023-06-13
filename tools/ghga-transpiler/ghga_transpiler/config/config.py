# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Module to process config file"""

from collections import Counter
from importlib import resources
from typing import Optional

import yaml
from pydantic import BaseModel, root_validator

from .exceptions import DuplicatedName


class DefaultSettings(BaseModel):
    """A data model for the defaults of the per-worksheet settings of a transpiler config"""

    start_row: int = 0
    start_column: int = 0
    end_column: int = 0


class WorksheetSettings(BaseModel):
    """A data model for the per-worksheet settings of a transpiler config"""

    name: str
    start_row: Optional[int]
    start_column: Optional[int]
    end_column: Optional[int]


class Worksheet(BaseModel):
    """A data model for worksheets in the transpiler config"""

    sheet_name: Optional[str]
    settings: Optional[WorksheetSettings]


class Config(BaseModel):
    """A data model for the transpiler config"""

    ghga_version: Optional[str]
    default_settings: DefaultSettings
    worksheets: list[Worksheet]

    @root_validator(pre=False)
    def get_param(cls, values):  # pylint: disable=no-self-argument
        """Function to manage parameters of global and worksheet specific configuration"""
        for sheet in values.get("worksheets"):
            for key in values.get("default_settings").__dict__:
                if getattr(sheet.settings, key) is None:
                    val = getattr(values.get("default_settings"), key)
                    setattr(sheet.settings, key, val)
        return values

    @root_validator(pre=False)
    def check_name(cls, values):  # pylint: disable=no-self-argument
        """Function to ensure that each worksheets has a unique sheet_name and name attributes."""
        # Check for duplicate attribute names
        attrs_counter = Counter(ws.settings.name for ws in values["worksheets"])
        dup_attrs = [name for name, count in attrs_counter.items() if count > 1]
        if dup_attrs:
            raise DuplicatedName(
                "Duplicate target attribute names: " + ", ".join(dup_attrs)
            )

        # Check for duplicate worksheet names
        attrs_counter = Counter(ws.sheet_name for ws in values["worksheets"])
        dup_ws_names = [name for name, count in attrs_counter.items() if count > 1]
        if dup_ws_names:
            raise DuplicatedName(
                "Duplicate worksheet names: " + ", ".join(dup_ws_names)
            )
        return values


def load_config(version: str) -> Config:
    """Reads configuration yaml file from default location and creates a Config object"""

    config_resource = resources.files("ghga_transpiler.configs").joinpath(
        f"{version}.yaml"
    )
    config_str = config_resource.read_text(encoding="utf8")
    return Config.parse_obj(yaml.full_load(config_str))
