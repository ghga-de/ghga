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

"""Integration tests for the reverse transpiler."""

from io import BytesIO

import pytest
from openpyxl import Workbook, load_workbook

from rts.models import StudyMetadata
from tests.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio()


def assert_workbooks_match(expected: Workbook, actual: Workbook) -> None:
    """Compare two workbooks for equality.

    This is more reliable than comparing bytestreams directly.
    """
    assert sorted(expected.sheetnames) == sorted(actual.sheetnames), (
        "Sheet names do not match"
    )

    for sheet_name in expected.sheetnames:
        expected_sheet = expected[sheet_name]
        actual_sheet = actual[sheet_name]

        expected_row_count = len([_ for _ in expected_sheet.rows])
        actual_row_count = len([_ for _ in actual_sheet.rows])
        assert expected_row_count == actual_row_count, (
            f"Row counts do not match for sheet: {sheet_name} (expected:"
            + f" {expected_row_count}, got: {actual_row_count})"
        )

        for row_index, row in enumerate(expected_sheet.iter_rows(), 1):
            for col_index, expected_cell in enumerate(row, 1):
                actual_value = actual_sheet.cell(row=row_index, column=col_index).value
                assert expected_cell.value == actual_value, (
                    f"Cell values do not match at {sheet_name} row {row_index},"
                    + f" column {col_index}. Expected: {expected_cell.value},"
                    + f" Got: {actual_value}"
                )


async def test_basic_reverse_transpilation(joint_fixture: JointFixture):
    """Test basic reverse transpilation functionality.

    This test relies on other tests examining the integrity of the transpiled workbook,
    as this test only checks that the workbook can be created and retrieved successfully.

    This test covers:
    - Upserting study metadata into the database
    - Retrieving the transpiled workbook by accession
    - Comparing the retrieved workbook to the expected one
    - Updating the workbook if it already exists
    - Deleting the workbook if it exists
    """
    reverse_transpiler = joint_fixture.reverse_transpiler

    # Load a sample study metadata JSON file into the database
    with open("tests/fixtures/test_artifact.json") as file:
        study_metadata_json = file.read()

    study_metadata = StudyMetadata.model_validate_json(study_metadata_json)
    accession = study_metadata.study_accession

    # Run the reverse transpilation manually so we have the output on hand to compare against
    expected_workbook = reverse_transpiler.reverse_transpile(study_metadata)
    assert isinstance(expected_workbook, Workbook)

    # Perform the reverse transpilation
    await reverse_transpiler.upsert_metadata(study_metadata=study_metadata)
    retrieved_workbook_bytes = await reverse_transpiler.retrieve_workbook(
        study_accession=accession
    )
    assert isinstance(retrieved_workbook_bytes, bytes)

    # Load the retrieved workbook and compare it to the expected one.
    retrieved_workbook = load_workbook(BytesIO(retrieved_workbook_bytes))
    assert isinstance(retrieved_workbook, Workbook)
    assert_workbooks_match(expected=expected_workbook, actual=retrieved_workbook)

    # Now call the REST API to get the transpiled data as well
    response = await joint_fixture.rest_client.get(f"/studies/{accession}")
    assert response.status_code == 200
    assert isinstance(response.content, bytes)

    assert response.headers["Content-Disposition"] == (
        f'attachment; filename="{accession}.xlsx"'
    )
    content_type = response.headers["Content-Type"]
    expected_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert content_type == expected_type

    # Check if the HTTP response content matches the expected workbook
    response_workbook = load_workbook(BytesIO(response.content))
    assert_workbooks_match(expected_workbook, response_workbook)

    # Update the study metadata and check that the workbook is updated
    study_metadata.content["samples"][0]["accession"] = "updated_sample_accession"
    updated_expected_workbook = reverse_transpiler.reverse_transpile(study_metadata)

    await reverse_transpiler.upsert_metadata(study_metadata=study_metadata)
    updated_retrieved_workbook_bytes = await reverse_transpiler.retrieve_workbook(
        study_accession=accession
    )
    updated_retrieved_bytestream = BytesIO(updated_retrieved_workbook_bytes)
    updated_retrieved_workbook = load_workbook(updated_retrieved_bytestream)

    # Make sure the workbooks match after the update
    assert_workbooks_match(
        expected=updated_expected_workbook, actual=updated_retrieved_workbook
    )

    # Make sure the new workbook is different from the old one
    with pytest.raises(AssertionError):
        assert_workbooks_match(
            expected=expected_workbook, actual=updated_retrieved_workbook
        )

    # Delete the workbook and check that it is deleted
    await reverse_transpiler.delete_metadata(study_accession=accession)
    msg = f"No workbook or metadata found for study accession '{accession}'"
    with pytest.raises(reverse_transpiler.MetadataNotFoundError, match=msg):
        await reverse_transpiler.retrieve_workbook(study_accession=accession)


async def test_retrieve_non_existent_workbook(joint_fixture: JointFixture):
    """Test that retrieving a workbook for a non-existent study accession fails.

    The happy path is tested in test_basic_reverse_transpilation.
    """
    reverse_transpiler = joint_fixture.reverse_transpiler

    msg = "No workbook or metadata found for study accession 'non_existent_accession'"
    with pytest.raises(reverse_transpiler.MetadataNotFoundError, match=msg):
        await reverse_transpiler.retrieve_workbook(
            study_accession="non_existent_accession"
        )


async def test_delete_non_existent_workbook(joint_fixture: JointFixture):
    """Test that deleting a non-existent workbook does not raise an error.

    The happy path is tested in test_basic_reverse_transpilation.
    """
    reverse_transpiler = joint_fixture.reverse_transpiler

    # This should not raise an error, even though the workbook does not exist
    await reverse_transpiler.delete_metadata(study_accession="non_existent_accession")


async def test_delete_non_existent_metadata(joint_fixture: JointFixture):
    """Test that deleting non-existent metadata does not raise an error.

    The happy path is tested in test_basic_reverse_transpilation.
    """
    reverse_transpiler = joint_fixture.reverse_transpiler

    # This should not raise an error, even though the metadata does not exist
    await reverse_transpiler.delete_metadata(study_accession="non_existent_accession")
