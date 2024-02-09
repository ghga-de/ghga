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

"""Test handling user sessions."""

from fastapi import status
from ghga_service_commons.api.testing import AsyncTestClient
from pytest import mark

from auth_service.auth_adapter.deps import get_session_store
from auth_service.config import CONFIG

from .fixtures import (  # noqa: F401
    fixture_client,
)


@mark.asyncio
async def test_logout(client: AsyncTestClient):
    """Test that a logout request removes the user session."""
    store = await get_session_store(config=CONFIG)
    session = await store.create_session()
    assert await store.get_session(session.session_id)
    # logout without cookie
    response = await client.post("/rpc/logout")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert await store.get_session(session.session_id)
    # logout with wrong cookie name
    response = await client.post(
        "/rpc/logout", cookies={"some-cookie": session.session_id}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert await store.get_session(session.session_id)
    # logout with wrong cookie value
    response = await client.post("/rpc/logout", cookies={"some-cookie": "some-id"})
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert await store.get_session(session.session_id)
    # logout with proper cookie
    response = await client.post(
        "/rpc/logout", cookies={"ghga_data_portal_sid": session.session_id}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not await store.get_session(session.session_id)
