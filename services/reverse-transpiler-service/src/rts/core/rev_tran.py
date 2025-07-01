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

"""Core functionality of the reverse transpiler service."""

import logging
from typing import Any, cast

import openpyxl
import openpyxl.styles
from openpyxl import Workbook
from openpyxl.cell.cell import Cell
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import Field
from pydantic_settings import BaseSettings

from rts.models import StudyMetadata
from rts.ports.inbound.rev_tran import ReverseTranspilerPort
from rts.ports.outbound.dao import MetadataDao, ResourceNotFoundError, WorkbookDaoPort

log = logging.getLogger(__name__)

# TODO: Add logging

# TODO: Check codebase for references to 'xlsx'

__all__ = ["ReverseTranspiler", "SheetNameConfig"]


class SheetNameConfig(BaseSettings):
    """Configuration for sheet names in the spreadsheet output."""

    sheet_names: dict[str, str] = Field(
        ...,
        description="Mapping of worksheet names to display names in the workbook.",
        examples=[
            {
                "analyses": "Analysis",
                "analysis_method_supporting_files": "AnalysisMethodSupportingFile",
            }
        ],
    )

    # Add a validator to check all the values in sheet_names to ensure they're under 31 characters
    @classmethod
    def validate_sheet_names(cls, values: dict[str, str]) -> dict[str, str]:
        """Ensure that all sheet names are under 31 characters."""
        for key, value in values.items():
            if len(value) > 31:
                raise ValueError(
                    f"Sheet name '{value}' for key '{key}' exceeds 31 characters."
                )
        return values


class ReverseTranspiler(ReverseTranspilerPort):
    """Provides functionality to convert study metadata from JSON files back into
    spreadsheet format.
    """

    def __init__(
        self,
        config: SheetNameConfig,
        metadata_dao: MetadataDao,
        workbook_dao: WorkbookDaoPort,
    ):
        self._config = config
        self._metadata_dao = metadata_dao
        self._workbook_dao = workbook_dao

    async def upsert_metadata(self, *, study_metadata: StudyMetadata) -> None:
        """Upsert study metadata in the database.

        This will run the reverse transpilation process and store the resulting XLSX,
        even if the metadata already exists.
        """
        do_upsert = True
        accession = study_metadata.study_accession
        try:
            existing_metadata = await self._metadata_dao.get_by_id(accession)
            log.debug(
                "Metadata for accession '%s' already exists, comparing...",
                accession,
            )
            if existing_metadata.model_dump() == study_metadata.model_dump():
                do_upsert = False
            else:
                log.info(
                    "Metadata for accession '%s' has changed, updating entry.",
                    accession,
                )
        except ResourceNotFoundError:
            log.debug(
                "No existing metadata found for accession '%s', creating new entry.",
                accession,
            )

        if not do_upsert:
            log.debug(
                "Metadata for accession '%s' has not changed, skipping upsert.",
                accession,
            )
            return

        await self._metadata_dao.upsert(study_metadata)

        log.debug("Transpiling metadata to workbook for accession '%s'.", accession)
        workbook = self.reverse_transpile(study_metadata)

        log.debug("Workbook created for accession '%s', upserting to DB.", accession)
        await self._workbook_dao.upsert(workbook=workbook, study_accession=accession)

    async def retrieve_metadata(self, *, study_accession: str) -> StudyMetadata:
        """Retrieve study metadata from the DAO by its accession.

        Raises MetadataNotFoundError if the metadata does not exist for the
        given study accession.
        """
        try:
            return await self._metadata_dao.get_by_id(study_accession)
        except ResourceNotFoundError as err:
            error = self.MetadataNotFoundError(study_accession=study_accession)
            log.error(error)
            raise error from err

    async def delete_metadata(self, *, study_accession: str) -> None:
        """Delete study metadata from the database by its accession.

        This method will always try to delete the associated workbook as well,
        regardless of whether the metadata exists or not.

        Does not raise an error if the metadata or workbook does not exist.
        """
        try:
            await self._metadata_dao.delete(study_accession)
        except ResourceNotFoundError:
            log.debug("Metadata for accession '%s' already deleted.", study_accession)

        await self._workbook_dao.delete(study_accession=study_accession)
        log.info("Workbook and metadata deleted for accession '%s'.", study_accession)

    async def retrieve_workbook(self, *, study_accession: str) -> bytes:
        """Retrieve the workbook for a given study accession.

        Args:
        - `study_accession`: The accession of the study metadata to retrieve.

        Raises MetadataNotFoundError if the workbook does not exist.

        Returns:
        - The workbook as bytes.
        """
        try:
            return await self._workbook_dao.find(study_accession=study_accession)
        except ResourceNotFoundError as err:
            error = self.MetadataNotFoundError(study_accession=study_accession)
            log.error(error)
            raise error from err

    def _rename_sheets(self, workbook: openpyxl.Workbook) -> None:
        """Rename sheets in the workbook to with configured values."""
        # Rename each sheet according to the mapping
        for sheet in workbook.worksheets:
            if sheet.title not in self._config.sheet_names:
                raise self.SheetNamingError(sheet_name=sheet.title)
            sheet.title = self._config.sheet_names[sheet.title]

    def _format_value(self, value: Any) -> Any:
        """Format values for cells, recursively formatting list and dict values."""
        output = value

        if isinstance(value, list):
            # Handle lists (like types, affiliations, etc.)
            formatted_values = [self._format_value(v) for v in value if v is not None]
            output = "; ".join(str(v) for v in formatted_values)
        elif isinstance(value, dict):
            # Handle dictionaries (like attributes)
            if value.keys() == {"key", "value"}:
                # If it's a {"key": x, "value": y} format, extract.
                output = f"{value['key']}={self._format_value(value['value'])}"
            else:
                # Format as key=value pairs for each item
                # output = json.dumps(formatted_value) TODO: Delete this if not needed
                output = ";".join(
                    f"{k}={self._format_value(v)}" for k, v in value.items()
                )

        return output

    def reverse_transpile(
        self,
        study_metadata: StudyMetadata,
    ) -> Workbook:
        """Convert StudyMetadata object to a workbook.

        Args:
        - `study_metadata`: The StudyMetadata instance to convert.

        Returns:
        - The metadata as an openpyxl Workbook.
        """
        # Extract the content and accession map
        content = study_metadata.content

        # Create a new workbook
        workbook = openpyxl.Workbook()

        # Remove the default sheet
        default_sheet = cast(Worksheet, workbook.active)
        workbook.remove(default_sheet)

        # Process each key in content
        for property_name, items in content.items():
            # If there are no items, continue to the next key
            if not items:
                continue

            # Create a new worksheet for this property
            worksheet: Worksheet = workbook.create_sheet(title=property_name)

            # Get the headers (keys from the first item)
            column_headers = list(items[0].keys())

            # Ensure 'alias' is the first column if present
            for idx, special_header in enumerate(["alias", "accession"]):
                if special_header in column_headers:
                    column_headers.remove(special_header)
                    column_headers.insert(idx, special_header)
                else:
                    log.info(  # Unsure of proper log level, or if this log is needed
                        "No '%s' field found in %s property for accession '%s'.",
                        special_header,
                        property_name,
                        study_metadata.study_accession,
                        extra={
                            "study_accession": study_metadata.study_accession,
                            "property": property_name,
                        },
                    )

            # Write the headers to the first row
            for col_idx, header in enumerate(column_headers, 1):
                cell: Cell = worksheet.cell(row=1, column=col_idx)
                cell.value = header
                cell.font = openpyxl.styles.Font(bold=True)
                worksheet.column_dimensions[cell.column_letter].width = 34

            # Process each item and write to the worksheet
            for row_idx, row_data in enumerate(
                items, 2
            ):  # Start from row 2 (after headers)
                for col_idx, header in enumerate(column_headers, 1):
                    cell: Cell = worksheet.cell(row=row_idx, column=col_idx)  # type: ignore

                    value = row_data.get(header)

                    formatted_value = self._format_value(value)
                    cell.value = formatted_value
                    # Set number format for numeric values
                    if isinstance(value, float | int) and not isinstance(value, bool):
                        cell.number_format = "0" if isinstance(value, int) else "0.00"

        # TODO: Move this up so we avoid the warnings in test
        self._rename_sheets(workbook)

        return workbook
