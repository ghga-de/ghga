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

"""Test the TOTP token DAO against the database."""

import pytest
from pydantic import SecretStr

from auth_service.auth_adapter.core.totp import TOTPHandler
from auth_service.auth_adapter.core.verify_totp import _token_state
from auth_service.auth_adapter.ports.dao import UserToken
from auth_service.auth_adapter.translators.dao import UserTokenDaoFactory
from auth_service.config import Config
from hexkit.protocols.dao import PreconditionFailedError
from hexkit.providers.mongodb.testutils import MongoDbFixture
from tests.fixtures.constants import ID_OF_JOHN

pytestmark = pytest.mark.asyncio()


async def test_token_update_with_precondition(mongodb: MongoDbFixture):
    """Test the precondition for writing back TOTP tokens against the database.

    It compares the nested fields of the token, including the encrypted secret.
    """
    config = Config(
        mongo_dsn=mongodb.config.mongo_dsn,
        db_name=mongodb.config.db_name,
        totp_encryption_key=SecretStr(TOTPHandler.random_encryption_key()),
    )
    factory = UserTokenDaoFactory(config=config, dao_factory=mongodb.dao_factory)
    token_dao = await factory.get_user_token_dao()
    totp_handler = TOTPHandler(config=config)
    user_token = UserToken(user_id=ID_OF_JOHN, totp_token=totp_handler.generate_token())
    await token_dao.upsert(user_token)

    # counters changed by an attempt are written if the token is unchanged
    read_state = _token_state(user_token)
    attempted = user_token.model_copy(deep=True)
    attempted.totp_token.last_counter = 42
    attempted.totp_token.total_attempts = 1
    await token_dao.update(attempted, precondition=read_state)
    assert await token_dao.get_by_id(ID_OF_JOHN) == attempted

    # but not if the counters have changed since they were read
    with pytest.raises(PreconditionFailedError):
        await token_dao.update(user_token, precondition=read_state)

    # nor if the token has been replaced with the same counters
    replaced = attempted.model_copy(deep=True)
    replaced.totp_token.encrypted_secret = (
        totp_handler.generate_token().encrypted_secret
    )
    await token_dao.upsert(replaced)
    with pytest.raises(PreconditionFailedError):
        await token_dao.update(attempted, precondition=_token_state(attempted))
    assert await token_dao.get_by_id(ID_OF_JOHN) == replaced
