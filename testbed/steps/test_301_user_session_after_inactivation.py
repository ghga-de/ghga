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

"""Step definition for user session after account inactivation"""

import pytest
from pytest_bdd import (  # noqa: RUF100
    given,
    scenarios,
    then,
    when,
)

from .conftest import JointFixture, Response, parse

scenarios("../features/301_user_session_after_inactivation.feature")


@then(
    parse('"{authorized_user_name}" changes the status of "{user_name}" to "{status}"'),
)
def user_account_inactivation(
    authorized_user_name: str,
    user_name: str,
    status: str,
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

    # Change user account status
    assert status in ["active", "inactive"]
    user_data = {
        "status": status,
    }
    url = f"{fixtures.config.ums_url}/users/{user_id}"
    headers = auth.headers(session=authorized_user_session)
    response = fixtures.http.patch(url, json=user_data, headers=headers)
    assert (
        response.status_code == 204
    ), f"Unable to update user status: { response.text}"
    sub = fixtures.auth.get_sub(user_name)
    fixtures.state.set_state(f"status-{sub}", status)


@given(parse('the status of "{full_name}" is "{status}"'))
def user_status(full_name: str, status: str, fixtures: JointFixture):
    sub = fixtures.auth.get_sub(full_name)
    saved_status = fixtures.state.get_state(f"status-{sub}")
    assert (
        saved_status
    ), f'Saved status "{saved_status}" does not match with the expected'


@when(parse('"{name}" tries to log in'), target_fixture="response")
def user_tries_to_login(name: str, fixtures: JointFixture) -> Response:
    sub = fixtures.auth.get_sub(name)
    email = fixtures.auth.get_email(name)
    external_token = fixtures.auth.oidc_login(
        name=name, email=email, sub=sub, valid_seconds=10
    )
    auth_headers = {"Authorization": f"Bearer {external_token}"}
    url = fixtures.config.auth_adapter_url + "/rpc/login"
    return fixtures.http.post(url, headers=auth_headers)


@then(parse('the response error message is "{expected_reason}"'))
def check_reason(expected_reason: str, response: Response):
    assert expected_reason in response.json()["detail"]
