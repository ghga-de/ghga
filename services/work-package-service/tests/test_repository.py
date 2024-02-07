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

"""Test the Work Package Repository."""

from ghga_service_commons.auth.ghga import AuthContext
from ghga_service_commons.utils.jwt_helpers import decode_and_validate_token
from pytest import mark, raises

from wps.core.models import (
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


@mark.asyncio(scope="session")
async def test_work_package_and_token_creation(
    repository: WorkPackageRepository, auth_context: AuthContext
):
    """Test creating a work package and a work order token"""
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
    work_package_id = creation_response.id
    encrypted_wpat = creation_response.token
    wpat = decrypt(encrypted_wpat)

    # retrieve work package

    with raises(repository.WorkPackageAccessError):
        await repository.get(
            work_package_id, check_valid=True, work_package_access_token="foo"
        )

    with raises(repository.WorkPackageAccessError):
        await repository.get(
            "invalid-id", check_valid=True, work_package_access_token=wpat
        )

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
    assert package.user_id == auth_context.id
    assert package.full_user_name == full_user_name
    assert package.email == auth_context.email
    assert package.token_hash == hash_token(wpat)
    assert (package.expires - package.created).days == 30

    # crate work order token

    with raises(repository.WorkPackageAccessError):
        await repository.work_order_token(
            work_package_id="invalid-work-package-id",
            file_id="file-id-1",
            work_package_access_token=wpat,
        )

    with raises(repository.WorkPackageAccessError):
        await repository.work_order_token(
            work_package_id=work_package_id,
            file_id="invalid-file-id",
            work_package_access_token=wpat,
        )

    with raises(repository.WorkPackageAccessError):
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
    assert wot_claims.pop("exp") - wot_claims.pop("iat") == 30
    assert wot_claims == {
        "type": package.type.value,
        "file_id": "file-id-3",
        "user_id": package.user_id,
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
    work_package_id = creation_response.id
    encrypted_wpat = creation_response.token
    wpat = decrypt(encrypted_wpat)

    # crate work order token

    with raises(repository.WorkPackageAccessError):
        await repository.work_order_token(
            work_package_id=work_package_id,
            file_id="non-existing-file",
            work_package_access_token=wpat,
        )

    with raises(repository.WorkPackageAccessError):
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
    assert wot_claims.pop("exp") - wot_claims.pop("iat") == 30
    assert wot_claims == {
        "type": package.type.value,
        "file_id": "file-id-1",
        "user_id": package.user_id,
        "user_public_crypt4gh_key": user_public_crypt4gh_key,
        "full_user_name": package.full_user_name,
        "email": package.email,
    }


@mark.asyncio(scope="session")
async def test_checking_accessible_datasets(
    repository: WorkPackageRepository, auth_context: AuthContext
):
    """Test checking the accessibility of datasets"""
    with raises(repository.DatasetNotFoundError):
        await repository.get_dataset("some-dataset_id")

    assert await repository.get_datasets(auth_context=auth_context) == []

    # announce dataset
    await repository.register_dataset(DATASET)

    assert await repository.get_dataset("some-dataset-id") == DATASET

    assert await repository.get_datasets(auth_context=auth_context) == [DATASET]


@mark.asyncio(scope="session")
async def test_deletion_of_datasets(
    repository: WorkPackageRepository, auth_context: AuthContext
):
    """Test deletion of existing datasets"""
    with raises(repository.DatasetNotFoundError):
        await repository.delete_dataset(DATASET.id)

    await repository.register_dataset(DATASET)
    assert await repository.get_dataset(DATASET.id) == DATASET

    await repository.delete_dataset(DATASET.id)

    with raises(repository.DatasetNotFoundError):
        await repository.delete_dataset(DATASET.id)
