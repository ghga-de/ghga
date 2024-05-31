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

"""Module to process config file"""

from collections import Counter
from collections.abc import Callable
from importlib import resources

import yaml
from pydantic import BaseModel, model_validator

from .exceptions import DuplicatedName, UnknownVersionError


class DefaultSettings(BaseModel):
    """A data model for the defaults of the per-worksheet settings of a transpiler config"""

    header_row: int = 0
    start_row: int = 0
    start_column: int = 0
    end_column: int = 0
    transformations: dict[str, Callable] = {}


class WorksheetSettings(BaseModel):
    """A data model for the per-worksheet settings of a transpiler config"""

    name: str
    header_row: int | None = None
    start_row: int | None = None
    start_column: int | None = None
    end_column: int | None = None
    transformations: dict[str, Callable] | None = None


class Worksheet(BaseModel):
    """A data model for worksheets in the transpiler config"""

    sheet_name: str
    settings: WorksheetSettings | None


class Config(BaseModel):
    """A data model for the transpiler config"""

    ghga_metadata_version: str
    default_settings: DefaultSettings
    worksheets: list[Worksheet]

    @model_validator(mode="after")
    def get_param(cls, values):  # noqa
        """Function to manage parameters of global and worksheet specific configuration"""
        for sheet in values.worksheets:
            for key in values.default_settings.__dict__:
                if getattr(sheet.settings, key) is None:
                    val = getattr(values.default_settings, key)
                    setattr(sheet.settings, key, val)
        return values

    @model_validator(mode="after")
    def check_name(cls, values):  # noqa
        """Function to ensure that each worksheets has a unique sheet_name and name attributes."""
        # Check for duplicate attribute names
        attrs_counter = Counter(ws.settings.name for ws in values.worksheets)
        dup_attrs = [name for name, count in attrs_counter.items() if count > 1]
        if dup_attrs:
            raise DuplicatedName(
                "Duplicate target attribute names: " + ", ".join(dup_attrs)
            )

        # Check for duplicate worksheet names
        attrs_counter = Counter(ws.sheet_name for ws in values.worksheets)
        dup_ws_names = [name for name, count in attrs_counter.items() if count > 1]
        if dup_ws_names:
            raise DuplicatedName(
                "Duplicate worksheet names: " + ", ".join(dup_ws_names)
            )
        return values


def load_config(version: str, package: resources.Package) -> Config:
    """Reads configuration yaml file from default location and creates a Config object"""
    config_resource = resources.files(package).joinpath(f"{version}.yaml")
    try:
        config_str = config_resource.read_text(encoding="utf8")
    except FileNotFoundError:
        # pylint: disable=raise-missing-from
        raise UnknownVersionError(f"Unknown metadata version: {version}") from None
    return Config.model_validate(yaml.load(config_str, yaml.Loader))  # noqa # nosec
