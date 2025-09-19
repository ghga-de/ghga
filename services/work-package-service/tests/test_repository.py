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

"""Test the Work Package Repository."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from ghga_service_commons.auth.ghga import AuthContext
from ghga_service_commons.utils.jwt_helpers import decode_and_validate_token
from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.utils import now_utc_ms_prec

from tests.fixtures.access import BOXES_WITH_UPLOAD_ACCESS, USERS_WITH_UPLOAD_ACCESS
from wps.config import Config
from wps.core.models import (
    BoxWithExpiration,
    Dataset,
    ResearchDataUploadBox,
    WorkPackage,
    WorkPackageCreationData,
    WorkPackageCreationResponse,
    WorkPackageType,
)
from wps.core.repository import WorkPackageRepository
from wps.core.tokens import generate_work_package_access_token, hash_token

from .fixtures import (  # noqa: F401
    SIGNING_KEY_PAIR,
    fixture_auth_context,
    fixture_config,
    fixture_repository,
)
from .fixtures.crypt import decrypt, user_public_crypt4gh_key
from .fixtures.datasets import DATASET

pytestmark = pytest.mark.asyncio()


async def test_work_package_and_token_creation(
    repository: WorkPackageRepository,
    auth_context: AuthContext,
    mongodb: MongoDbFixture,
    config: Config,
):
    """Test creating a work package and a work order token"""
    valid_days = config.work_package_valid_days

    # announce dataset
    await repository.register_dataset(DATASET)

    # create work package for all files

    creation_data = WorkPackageCreationData(
        dataset_id="some-dataset-id",
        type=WorkPackageType.DOWNLOAD,
        file_ids=None,
        user_public_crypt4gh_key=user_public_crypt4gh_key,
    )

    creation_response = await repository.create(
        creation_data=creation_data, auth_context=auth_context
    )

    assert isinstance(creation_response, WorkPackageCreationResponse)

    expires = creation_response.expires
    assert (
        round((expires - now_utc_ms_prec()).total_seconds() / (24 * 60 * 60))
        == valid_days
    )

    work_package_id = UUID(creation_response.id)
    encrypted_wpat = creation_response.token
    wpat = decrypt(encrypted_wpat)

    # retrieve work package

    with pytest.raises(repository.WorkPackageAccessError):
        await repository.get(
            work_package_id, check_valid=True, work_package_access_token="foo"
        )

    with pytest.raises(repository.WorkPackageAccessError):
        await repository.get(uuid4(), check_valid=True, work_package_access_token=wpat)

    package = await repository.get(
        work_package_id, check_valid=True, work_package_access_token=wpat
    )

    full_user_name = (auth_context.title or "Tester") + " " + auth_context.name

    assert isinstance(package, WorkPackage)
    assert package.dataset_id == "some-dataset-id"
    assert package.type == WorkPackageType.DOWNLOAD
    assert package.files == {
        "file-id-1": ".json",
        "file-id-2": ".csv",
        "file-id-3": ".bam",
    }
    assert package.user_public_crypt4gh_key == user_public_crypt4gh_key
    assert package.user_id == UUID(auth_context.id)
    assert package.full_user_name == full_user_name
    assert package.email == auth_context.email
    assert package.token_hash == hash_token(wpat)
    assert (package.expires - package.created).days == valid_days

    # crate work order token

    with pytest.raises(repository.WorkPackageAccessError):
        await repository.get_download_wot(
            work_package_id=uuid4(),
            file_id="file-id-1",
            work_package_access_token=wpat,
        )

    with pytest.raises(repository.WorkPackageAccessError):
        await repository.get_download_wot(
            work_package_id=work_package_id,
            file_id="invalid-file-id",
            work_package_access_token=wpat,
        )

    with pytest.raises(repository.WorkPackageAccessError):
        await repository.get_download_wot(
            work_package_id=work_package_id,
            file_id="file-id-1",
            work_package_access_token="invalid-token",
        )

    wot = await repository.get_download_wot(
        work_package_id=work_package_id,
        file_id="file-id-3",
        work_package_access_token=wpat,
    )
    assert wot is not None

    # check the content of the work order token

    wot = decrypt(wot)
    wot_claims = decode_and_validate_token(wot, SIGNING_KEY_PAIR.public())
    assert wot_claims.pop("exp") - wot_claims.pop("iat") == valid_days
    assert wot_claims == {
        "work_type": package.type.value,
        "file_id": "file-id-3",
        "user_public_crypt4gh_key": user_public_crypt4gh_key,
    }

    # create another work package for specific files

    creation_data = WorkPackageCreationData(
        dataset_id="some-dataset-id",
        type=WorkPackageType.DOWNLOAD,
        file_ids=["file-id-1", "file-id-3", "non-existing-file"],
        user_public_crypt4gh_key=user_public_crypt4gh_key,
    )

    creation_response = await repository.create(
        creation_data=creation_data, auth_context=auth_context
    )

    assert isinstance(creation_response, WorkPackageCreationResponse)
    work_package_id = UUID(creation_response.id)
    encrypted_wpat = creation_response.token
    wpat = decrypt(encrypted_wpat)

    # crate work order token
    with pytest.raises(repository.WorkPackageAccessError):
        await repository.get_download_wot(
            work_package_id=work_package_id,
            file_id="non-existing-file",
            work_package_access_token=wpat,
        )

    with pytest.raises(repository.WorkPackageAccessError):
        await repository.get_download_wot(
            work_package_id=work_package_id,
            file_id="file-id-2",
            work_package_access_token=wpat,
        )

    wot = await repository.get_download_wot(
        work_package_id=work_package_id,
        file_id="file-id-1",
        work_package_access_token=wpat,
    )
    assert wot is not None

    # check the content of the work order token

    wot = decrypt(wot)
    wot_claims = decode_and_validate_token(wot, SIGNING_KEY_PAIR.public())
    assert wot_claims.pop("exp") - wot_claims.pop("iat") == valid_days
    assert wot_claims == {
        "work_type": package.type.value,
        "file_id": "file-id-1",
        "user_public_crypt4gh_key": user_public_crypt4gh_key,
    }

    # revoke access and check that work order token cannot be created any more
    async def check_download_access_patched(
        user_id: str, dataset_id: str
    ) -> UTCDatetime | None:
        assert user_id == package.user_id
        assert dataset_id == package.dataset_id
        return None

    access = repository._access
    _check_download_access_original = access.check_download_access
    try:
        access.check_download_access = check_download_access_patched  # type: ignore
        with pytest.raises(repository.WorkPackageAccessError):
            await repository.get_download_wot(
                work_package_id=work_package_id,
                file_id="file-id-1",
                work_package_access_token=wpat,
            )
    finally:
        access.check_download_access = _check_download_access_original  # type: ignore


async def test_checking_accessible_datasets(
    repository: WorkPackageRepository,
    auth_context: AuthContext,
    mongodb: MongoDbFixture,
):
    """Test checking the accessibility of datasets"""
    with pytest.raises(repository.DatasetNotFoundError):
        await repository.get_dataset("some-dataset_id")

    assert await repository.get_datasets(auth_context=auth_context) == []

    # announce dataset
    await repository.register_dataset(DATASET)

    assert await repository.get_dataset("some-dataset-id") == DATASET

    datasets_with_expiration = await repository.get_datasets(auth_context=auth_context)
    assert len(datasets_with_expiration) == 1
    dataset_with_expiration = datasets_with_expiration[0]

    expires = dataset_with_expiration.expires
    assert round((expires - now_utc_ms_prec()).total_seconds() / (24 * 60 * 60)) == 365

    dataset = Dataset(**dataset_with_expiration.model_dump(exclude={"expires"}))
    assert dataset == DATASET


async def test_deletion_of_datasets(
    repository: WorkPackageRepository, mongodb: MongoDbFixture
):
    """Test deletion of existing datasets"""
    with pytest.raises(repository.DatasetNotFoundError):
        await repository.delete_dataset(DATASET.id)

    await repository.register_dataset(DATASET)
    assert await repository.get_dataset(DATASET.id) == DATASET

    await repository.delete_dataset(DATASET.id)

    with pytest.raises(repository.DatasetNotFoundError):
        await repository.delete_dataset(DATASET.id)


async def test_retrieve_work_package_without_box_id(
    repository: WorkPackageRepository, mongodb: MongoDbFixture
):
    """Test retrieving an existing WorkPackage document from the database and
    using that to create a WorkPackage pydantic model instance, ensuring that no errors
    are raised when `box_id` is not included as a kwarg.
    """
    # Create an old-style work package document directly in the database (without box_id)
    old_work_package_id = uuid4()
    user_id = uuid4()
    created_time = now_utc_ms_prec()
    expires_time = created_time + timedelta(days=30)
    token = generate_work_package_access_token()

    # This document represents an old work package as it would exist before the upload feature
    old_document = {
        "_id": old_work_package_id,
        "dataset_id": "some-old-dataset-id",
        "type": "download",
        "files": {"file-1": ".json", "file-2": ".csv"},
        "user_id": user_id,
        "full_user_name": "Dr. Legacy User",
        "email": "legacy@example.com",
        "user_public_crypt4gh_key": "some-legacy-key",
        "token_hash": hash_token(token),
        "created": created_time,
        "expires": expires_time,
    }

    # Insert the old document directly into MongoDB using the mongodb fixture
    # Access the collection through the mongodb fixture
    db = mongodb.client[mongodb.config.db_name]
    collection = db["workPackages"]
    collection.insert_one(old_document)

    # Now retrieve the work package through the repository
    # This should work without errors even though box_id is missing
    retrieved_package = await repository.get(
        work_package_id=old_work_package_id,
        check_valid=False,  # don't need to check access, just see if the retrieval works
        work_package_access_token=token,
    )

    # Verify basic details to see if the work package was retrieved correctly
    assert retrieved_package.id == old_work_package_id
    assert retrieved_package.dataset_id == "some-old-dataset-id"
    assert retrieved_package.box_id is None  # Should be None for old documents


async def test_box_crud(
    repository: WorkPackageRepository, mongodb: MongoDbFixture, config: Config
):
    """Test box insertion, retrieval, and deletion."""
    db = mongodb.client[mongodb.config.db_name]
    collection = db[config.upload_boxes_collection]
    box_id = uuid4()
    file_upload_box_id = uuid4()
    box = ResearchDataUploadBox(
        id=box_id,
        file_upload_box_id=file_upload_box_id,
        title="My Upload",
        description="abc123",
    )
    doc = {
        "_id": box_id,
        "file_upload_box_id": file_upload_box_id,
        "title": "My Upload",
        "description": "abc123",
    }

    # Register
    await repository.register_upload_box(box)
    inserted = collection.find().to_list()
    assert len(inserted) == 1
    assert inserted[0] == doc

    # Get
    retrieved = await repository.get_upload_box(box_id=box_id)
    assert retrieved.model_dump() == box.model_dump()

    # Delete
    await repository.delete_upload_box(box_id=box_id)
    remaining_docs = collection.find().to_list()
    assert len(remaining_docs) == 0


async def test_box_crud_error_handling(
    repository: WorkPackageRepository, mongodb: MongoDbFixture, config: Config
):
    """Test error handling for the upload box crud methods."""
    # Delete box that doesn't exist - should not see any error
    await repository.delete_upload_box(box_id=uuid4())

    # Get box that doesn't exist - should get an error
    with pytest.raises(WorkPackageRepository.UploadBoxNotFoundError):
        await repository.get_upload_box(box_id=uuid4())

    # Register box twice - should not see an error
    box_id = uuid4()
    box = ResearchDataUploadBox(
        id=box_id,
        file_upload_box_id=uuid4(),
        title="My Upload",
        description="abc123",
    )
    await repository.register_upload_box(box)
    await repository.register_upload_box(box)

    # Verify that there is only one doc in the box collection
    db = mongodb.client[mongodb.config.db_name]
    collection = db[config.upload_boxes_collection]
    inserted = collection.find().to_list()
    assert len(inserted) == 1
    assert inserted[0]["_id"] == box_id


async def test_get_boxes(repository: WorkPackageRepository, mongodb: MongoDbFixture):
    """Test retrieving multiple boxes based on user ID."""
    # Insert some boxes
    box_ids = BOXES_WITH_UPLOAD_ACCESS
    boxes = [
        ResearchDataUploadBox(
            id=box_ids[i],
            file_upload_box_id=uuid4(),
            title=f"Box{i}",
            description=f"This is upload box #{i}",
        )
        for i in range(len(box_ids))
    ]
    boxes.sort(key=lambda x: x.id)

    for box in boxes:
        await repository.register_upload_box(box)

    # Mock the access API to tell us the test user has access to those boxes
    user_id = USERS_WITH_UPLOAD_ACCESS[0]

    # Try with random user ID - should get an empty list
    boxes_with_expiration: list[BoxWithExpiration] = await repository.get_upload_boxes(
        user_id=uuid4()
    )
    assert not boxes_with_expiration

    # Try for real
    boxes_with_expiration = await repository.get_upload_boxes(user_id=user_id)
    assert boxes_with_expiration
    assert len(boxes_with_expiration) == 2
    boxes_with_expiration.sort(key=lambda x: x.id)
