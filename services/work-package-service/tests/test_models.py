# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test the creation of dataclasses and DTOs"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from wps.core.models import (
    DownloadWorkOrder,
    UploadWorkOrderTokenRequest,
    WorkPackage,
    WorkPackageCreationData,
    WorkPackageType,
)

from .fixtures.crypt import user_public_crypt4gh_key


def test_upload_wot_request_model():
    """Test validation for the UploadWorkOrderTokenRequest model"""
    _ = UploadWorkOrderTokenRequest(work_type="create", alias="test", file_id=None)
    _ = UploadWorkOrderTokenRequest(work_type="upload", alias=None, file_id=uuid4())
    _ = UploadWorkOrderTokenRequest(work_type="close", alias=None, file_id=uuid4())
    _ = UploadWorkOrderTokenRequest(work_type="delete", alias=None, file_id=uuid4())

    for work_type in ["create", "close", "upload", "delete"]:
        with pytest.raises(ValueError):
            _ = UploadWorkOrderTokenRequest(
                work_type=work_type,  # type: ignore
                alias=None,
                file_id=None,
            )


def test_work_order_token():
    """Test instantiating a work order token model."""
    token = DownloadWorkOrder(
        file_id="some-file-id",
        user_public_crypt4gh_key="some-public-key",
    )
    assert token.file_id == "some-file-id"

    with pytest.raises(ValueError):
        token = DownloadWorkOrder(
            work_type="upload",  # type: ignore
            file_id="some_file_id",
            user_public_crypt4gh_key="some-public-key",
        )


def test_good_creation_data():
    """Test instantiating valid work package creation DTO."""
    data = WorkPackageCreationData(
        dataset_id="some-dataset-id",
        type=WorkPackageType.DOWNLOAD,
        file_ids=["some-file-id", "another-file-id"],
        user_public_crypt4gh_key=user_public_crypt4gh_key,
    )
    assert data.dataset_id == "some-dataset-id"
    assert data.type == WorkPackageType.DOWNLOAD
    assert data.file_ids == ["some-file-id", "another-file-id"]
    assert data.user_public_crypt4gh_key == user_public_crypt4gh_key

    wrapped_key = (
        "\n\n-----BEGIN CRYPT4GH PUBLIC KEY-----\n"
        + user_public_crypt4gh_key
        + "\n-----END CRYPT4GH PUBLIC KEY-----\n\n"
    )
    test_box_id = uuid4()
    data = WorkPackageCreationData(
        box_id=test_box_id,
        type=WorkPackageType.UPLOAD,
        file_ids=None,
        user_public_crypt4gh_key=wrapped_key,
    )
    assert data.box_id == test_box_id
    assert data.type == WorkPackageType.UPLOAD
    assert data.file_ids is None
    assert data.user_public_crypt4gh_key == user_public_crypt4gh_key


def test_bad_creation_data():
    """Test instantiating invalid work package creation DTO."""
    with pytest.raises(ValidationError, match="dataset_id"):
        WorkPackageCreationData(
            dataset_id=["foo", "bar"],  # type: ignore
            type=WorkPackageType.DOWNLOAD,
            file_ids=["some-file-id", "another-file-id"],
            user_public_crypt4gh_key=user_public_crypt4gh_key,
        )
    with pytest.raises(ValidationError, match="type"):
        WorkPackageCreationData(
            dataset_id="some-dataset-id",
            type="UNKNOWN_TYPE",  # type: ignore
            file_ids=["some-file-id", "another-file-id"],
            user_public_crypt4gh_key=user_public_crypt4gh_key,
        )
    with pytest.raises(ValidationError, match="file_ids"):
        WorkPackageCreationData(
            dataset_id="some-dataset-id",
            type=WorkPackageType.DOWNLOAD,
            file_ids="some-file-id",  # type: ignore
            user_public_crypt4gh_key=user_public_crypt4gh_key,
        )
    with pytest.raises(ValidationError, match="user_public_crypt4gh_key"):
        WorkPackageCreationData(
            dataset_id="some-dataset-id",
            type=WorkPackageType.DOWNLOAD,
            file_ids=["some-file-id", "another-file-id"],
            user_public_crypt4gh_key="foo",
        )


TEST_ID = UUID("edd537d0-0b94-4305-bfe0-99863aa63998")


def test_work_package():
    """Test instantiating a work package DTO."""
    package = WorkPackage(
        id=TEST_ID,
        user_id=uuid4(),
        dataset_id="some-dataset-id",
        type=WorkPackageType.DOWNLOAD,
        files={"some-file-id": ".sam", "another-file-id": ".bam"},
        user_public_crypt4gh_key=user_public_crypt4gh_key,
        full_user_name="Dr. John Doe",
        email="john@home.org",
        token_hash="308eda9daf26b7446b284449a5895ab9a04ff30c129d4454e471cfb81bf5557d",
        created=datetime(2022, 2, 2, 2, tzinfo=UTC),  # pyright: ignore
        expires=datetime(2022, 2, 2, 3, tzinfo=UTC),  # pyright: ignore
    )
    assert package.id == TEST_ID
    assert package.full_user_name == "Dr. John Doe"
    assert package.files is not None
    assert package.files["another-file-id"] == ".bam"
    assert (package.expires - package.created).seconds == 60 * 60


@pytest.mark.parametrize(
    "dataset_id,box_id,work_type,expected_error",
    [
        pytest.param(
            "some-dataset-id",
            None,
            WorkPackageType.UPLOAD,
            "dataset_id shouldn't be provided for upload work packages",
            id="UploadWithDatasetId",
        ),
        pytest.param(
            None,
            None,
            WorkPackageType.UPLOAD,
            "box_id is required for upload work packages",
            id="UploadWithoutBoxId",
        ),
        pytest.param(
            "some-dataset-id",
            None,
            WorkPackageType.UPLOAD,
            "box_id is required for upload work packages; dataset_id shouldn't be provided for upload work packages",
            id="UploadWithBothProblems",
        ),
        pytest.param(
            None,
            None,
            WorkPackageType.DOWNLOAD,
            "dataset_id is required for download work packages",
            id="DownloadWithoutDatasetId",
        ),
        pytest.param(
            "some-dataset-id",
            uuid4(),
            WorkPackageType.DOWNLOAD,
            "box_id shouldn't be provided for download work packages",
            id="DownloadWithBoxId",
        ),
        pytest.param(
            None,
            uuid4(),
            WorkPackageType.DOWNLOAD,
            "dataset_id is required for download work packages; box_id shouldn't be provided for download work packages",
            id="DownloadWithBothProblems",
        ),
    ],
)
def test_work_package_creation_data_validation(
    dataset_id, box_id, work_type, expected_error
):
    """Test validation of dataset_id/box_id requirements for different work package types."""
    with pytest.raises(ValidationError, match=expected_error):
        WorkPackageCreationData(
            dataset_id=dataset_id,
            box_id=box_id,
            type=work_type,
            user_public_crypt4gh_key=user_public_crypt4gh_key,
        )
