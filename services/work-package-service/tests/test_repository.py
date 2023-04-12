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

from datetime import timedelta

from ghga_service_commons.auth.ghga import AuthContext
from ghga_service_commons.utils.jwt_helpers import decode_and_validate_token
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.providers.mongodb.testutils import (  # noqa: F401; pylint: disable=unused-import
    mongodb_fixture,
)
from pydantic import SecretStr
from pytest import mark, raises

from wps.adapters.outbound.dao import WorkPackageDaoConstructor
from wps.core.models import (
    WorkPackage,
    WorkPackageCreationData,
    WorkPackageCreationResponse,
    WorkType,
)
from wps.core.repository import WorkPackageConfig, WorkPackageRepository
from wps.core.tokens import hash_token

from .fixtures import AUTH_CLAIMS, SIGNING_KEY_PAIR
from .fixtures.crypt import decrypt, user_public_crypt4gh_key

work_package_config = WorkPackageConfig(
    work_package_signing_key=SecretStr(SIGNING_KEY_PAIR.export_private()),
)


@mark.asyncio
async def test_work_package_repository(
    mongodb_fixture,  # noqa: F811  pylint:disable=redefined-outer-name
):
    """Test creating a work package and a work order token"""

    # create repository

    work_package_dao = await WorkPackageDaoConstructor.construct(
        config=work_package_config,
        dao_factory=mongodb_fixture.dao_factory,
    )
    repository = WorkPackageRepository(
        config=work_package_config, work_package_dao=work_package_dao
    )

    # create work package

    iat = now_as_utc() - timedelta(1)  # validy is assumed by the repository
    auth_context = AuthContext(**AUTH_CLAIMS, iat=iat, exp=iat)

    creation_data = WorkPackageCreationData(
        dataset_id="some-dataset-id",
        type=WorkType.DOWNLOAD,
        file_ids=["some-file-id", "another-file-id"],
        user_public_crypt4gh_key=user_public_crypt4gh_key,
    )

    creation_response = await repository.create(creation_data, auth_context)

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

    assert isinstance(package, WorkPackage)
    assert package.dataset_id == "some-dataset-id"
    assert package.type == WorkType.DOWNLOAD
    assert package.file_ids == ["some-file-id", "another-file-id"]
    assert package.file_extensions == {}
    assert package.user_public_crypt4gh_key == user_public_crypt4gh_key
    assert package.user_id == auth_context.id
    assert package.full_user_name == auth_context.title + " " + auth_context.name
    assert package.email == auth_context.email
    assert package.token_hash == hash_token(wpat)
    assert (package.expires - package.created).days == 30

    # crate work order token

    with raises(repository.WorkPackageAccessError):
        await repository.work_order_token(
            "invalid-work-package-id", "some-file-id", work_package_access_token=wpat
        )

    with raises(repository.WorkPackageAccessError):
        await repository.work_order_token(
            work_package_id, "invalid-file-id", work_package_access_token=wpat
        )

    with raises(repository.WorkPackageAccessError):
        await repository.work_order_token(
            work_package_id, "some-file-id", work_package_access_token="invalid-token"
        )

    wot = await repository.work_order_token(
        work_package_id, "some-file-id", work_package_access_token=wpat
    )
    assert wot is not None

    # check the content of the work order token

    wot = decrypt(wot)
    wot_claims = decode_and_validate_token(wot, SIGNING_KEY_PAIR.public())
    assert wot_claims.pop("exp") - wot_claims.pop("iat") == 30
    assert wot_claims == {
        "type": package.type.value,
        "file_id": "some-file-id",
        "user_id": package.user_id,
        "public_key": user_public_crypt4gh_key,
        "full_user_name": package.full_user_name,
        "email": package.email,
    }
