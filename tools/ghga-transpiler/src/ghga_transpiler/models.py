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

"""This module contains the models describing a GHGA Workbook."""

from collections import Counter

from pydantic import BaseModel, Field, model_serializer, model_validator

from .exceptions import DuplicatedName


class GHGAWorksheetRow(BaseModel):
    """A model defining a row in a worksheet encompassing a content and the relations
    keeping the references to other classes.
    """

    relations: dict = Field(
        ...,
        description="A dictionary mapping resource identifiers to their"
        + " corresponding classes. This field details the resources referenced within"
        + " the worksheet row.",
    )

    content: dict = Field(
        ...,
        description="A dictionary containing key-value pairs where keys"
        + " represent the properties of the data fields, and values represent"
        + " the corresponding data. This field does not include information"
        + " about the relations.",
    )


class GHGAWorksheet(BaseModel):
    """A model defining a GHGA worksheet."""

    worksheet: dict[str, dict[str, GHGAWorksheetRow]] = Field(
        ...,
        description="A nested dictionary representing a GHGA worksheet."
        + " The outer dictionary maps worksheet names (strings) to inner dictionaries."
        + " Each inner dictionary maps row primary key values (strings) to their"
        + " corresponding `GHGAWorksheetRow` instances.",
    )

    @model_serializer()
    def serialize_model(self):
        """Custom serializer method that returns a dictionary representation of the
        worksheet, omitting the attribute name 'worksheet' from the serialized output.
        """
        return {key: value for key, value in self.worksheet.items()}


class GHGAWorkbook(BaseModel):
    """A model defining a GHGA workbook consists of multiple worksheets."""

    workbook: tuple[GHGAWorksheet, ...] = Field(
        ...,
        description="A tuple of `GHGAWorksheet` instances."
        + "Each `GHGAWorksheet` represents a worksheet within the workbook.",
    )

    @model_validator(mode="after")
    def check_name(cls, values):  # noqa
        """Function to ensure that workbook consists of worksheets with unique names."""
        attrs_counter = Counter(
            key for ws in values.workbook for key, _ in ws.worksheet.items()
        )
        dup_ws_names = [name for name, count in attrs_counter.items() if count > 1]
        if dup_ws_names:
            raise DuplicatedName(
                "Duplicate worksheet names:: " + ", ".join(dup_ws_names)
            )
        return values

    @model_serializer()
    def serialize_model(self):
        """Custom serializer method that returns a dictionary representation of the
        workbook, omitting the attribute name 'workbook' from the serialized output and
        returning a flattened dictionary instead of a tuple of worksheets.
        """
        return {
            key: value
            for worksheet in self.workbook
            for key, value in worksheet.worksheet.items()
        }
