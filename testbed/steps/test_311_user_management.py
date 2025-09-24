# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Step definitions for user management"""

import pytest

from .conftest import (
    JointFixture,
    Response,
    given,
    parse,
    scenarios,
    then,
    when,
)

scenarios("../features/311_user_management.feature")


@when(parse('"{full_name}" retrieves the list of all users'), target_fixture="response")
def retrieve_list_of_users(full_name: str, fixtures: JointFixture):
    """Retrieve the list of all registered users."""
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    assert session.user_id, f"user_id is missing for {full_name}"

    url = f"{fixtures.config.ums_url}/users"
    headers = fixtures.auth.headers(session=session)
    return fixtures.http.get(url, headers=headers)


@then("I get the details of all registered users")
def validate_user_list(response: Response, fixtures: JointFixture):
    results = response.json()
    assert len(results) > 0, "Expected at least one user in the list"
    registered_users = fixtures.state.get_state("registered users") or {}
    assert len(results) == len(registered_users), (
        "Number of users does not match the number of registered users"
    )
    assert sorted([i["ext_id"] for i in results]) == sorted(registered_users.keys()), (
        "User IDs in the response do not match the registered users"
    )


@when(parse('"{authorized_user_name}" deletes the user "{user_name}"'))
def delete_user_account(
    authorized_user_name: str,
    user_name: str,
    fixtures: JointFixture,
):
    auth = fixtures.auth

    user_session = fixtures.auth.get_saved_session(
        name=user_name, state_store=fixtures.state
    )  # Get existing session of active in user
    assert user_session

    user_id = user_session.user_id
    assert user_id

    authorized_user_session = fixtures.auth.get_saved_session(
        name=authorized_user_name, state_store=fixtures.state
    )

    url = f"{fixtures.config.ums_url}/users/{user_id}"
    headers = auth.headers(session=authorized_user_session)
    response = fixtures.http.delete(url, headers=headers)
    assert response.status_code == 204, f"Unable to delete user: {response.text}"
    sub = fixtures.auth.get_sub(user_name)

    # Clean the state
    fixtures.state.unset_state(f"totp-token-{sub}")
    fixtures.state.unset_state(f"session-{sub}")
    registered_users = fixtures.state.get_state("registered users") or {}
    if sub in registered_users:
        del registered_users[sub]
        fixtures.state.set_state("registered users", registered_users)


@then(parse('the user status of "{full_name}" is "{status}"'))
def validate_user_status_in_response(
    full_name: str, status: str, response: Response, fixtures: JointFixture
):
    """Validate the status of a user in the response.

    Takes the user list as response of UMS endpoint
    """
    user_list = response.json()
    assert len(user_list)
    user_status = {u["ext_id"]: u["status"] for u in user_list}
    sub = fixtures.auth.get_sub(full_name)
    assert sub in user_status
    assert user_status[sub] == status, (
        f"Expected status for user {full_name} ({sub}) is {status}, "
        f"but got {user_status[sub]}"
    )
