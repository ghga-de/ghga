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

from uuid import UUID, uuid4

import pytest
from ghga_service_commons.auth.ghga import AuthContext
from ghga_service_commons.utils.jwt_helpers import decode_and_validate_token
from ghga_service_commons.utils.utc_dates import UTCDatetime, now_as_utc
from hexkit.providers.mongodb.testutils import MongoDbFixture

from wps.config import Config
from wps.core.models import (
    Dataset,
    WorkPackage,
    WorkPackageCreationData,
    WorkPackageCreationResponse,
    WorkType,
)
from wps.core.repository import WorkPackageRepository
from wps.core.tokens import hash_token

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
        type=WorkType.DOWNLOAD,
        file_ids=None,
        user_public_crypt4gh_key=user_public_crypt4gh_key,
    )

    creation_response = await repository.create(
        creation_data=creation_data, auth_context=auth_context
    )

    assert isinstance(creation_response, WorkPackageCreationResponse)

    expires = creation_response.expires
    assert (
        round((expires - now_as_utc()).total_seconds() / (24 * 60 * 60)) == valid_days
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
    assert package.type == WorkType.DOWNLOAD
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
        await repository.work_order_token(
            work_package_id=uuid4(),
            file_id="file-id-1",
            work_package_access_token=wpat,
        )

    with pytest.raises(repository.WorkPackageAccessError):
        await repository.work_order_token(
            work_package_id=work_package_id,
            file_id="invalid-file-id",
            work_package_access_token=wpat,
        )

    with pytest.raises(repository.WorkPackageAccessError):
        await repository.work_order_token(
            work_package_id=work_package_id,
            file_id="file-id-1",
            work_package_access_token="invalid-token",
        )

    wot = await repository.work_order_token(
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
        "type": package.type.value,
        "file_id": "file-id-3",
        "user_id": str(package.user_id),
        "user_public_crypt4gh_key": user_public_crypt4gh_key,
        "full_user_name": package.full_user_name,
        "email": package.email,
    }

    # create another work package for specific files

    creation_data = WorkPackageCreationData(
        dataset_id="some-dataset-id",
        type=WorkType.DOWNLOAD,
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
        await repository.work_order_token(
            work_package_id=work_package_id,
            file_id="non-existing-file",
            work_package_access_token=wpat,
        )

    with pytest.raises(repository.WorkPackageAccessError):
        await repository.work_order_token(
            work_package_id=work_package_id,
            file_id="file-id-2",
            work_package_access_token=wpat,
        )

    wot = await repository.work_order_token(
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
        "type": package.type.value,
        "file_id": "file-id-1",
        "user_id": str(package.user_id),
        "user_public_crypt4gh_key": user_public_crypt4gh_key,
        "full_user_name": package.full_user_name,
        "email": package.email,
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
            await repository.work_order_token(
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
    assert round((expires - now_as_utc()).total_seconds() / (24 * 60 * 60)) == 365

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
