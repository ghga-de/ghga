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

"""Unit tests for the utils module."""

from pytest import mark

from auth_service.user_management.claims_repository.core.utils import (
    is_data_steward,
    user_exists,
)

from ....fixtures.utils import DummyClaimDao, DummyUserDao


@mark.asyncio
async def test_user_exists():
    """Test that existence of users can be checked."""
    user_dao = DummyUserDao(id_="some-internal-id")
    assert await user_exists(None, user_dao) is False  # type: ignore
    assert await user_exists("some-internal-id", user_dao) is True
    assert await user_exists("other-internal-id", user_dao) is False


@mark.asyncio
async def test_is_data_steward():
    """Test check that a user is a data steward."""
    claim_dao = DummyClaimDao()
    user_dao = DummyUserDao(id_="james@ghga.de")
    assert await is_data_steward("james@ghga.de", user_dao, claim_dao)
    assert not await is_data_steward("john@ghga.de", user_dao, claim_dao)
    assert not await is_data_steward(
        "james@ghga.de", user_dao, claim_dao, now=lambda: claim_dao.invalid_date
    )
    user_dao = DummyUserDao("jane@ghga.de")
    assert not await is_data_steward("james@ghga.de", user_dao, claim_dao)
    assert not await is_data_steward("john@ghga.de", user_dao, claim_dao)
