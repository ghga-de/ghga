# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Step definitions for user authentication and registration"""

from datetime import datetime, timedelta

from ghga_service_commons.utils.utc_dates import now_as_utc

from .conftest import (
    JointFixture,
    Response,
    given,
    parse,
    scenarios,
    then,
    when,
)

scenarios("../features/30_user_registration.feature")


@given(parse('the user "{full_name}" is not yet registered'))
def user_not_yet_registered(full_name: str, fixtures: JointFixture):
    registered_users = fixtures.state.get_state("registered users") or {}
    sub = fixtures.auth.get_sub(full_name)
    if not fixtures.config.use_api_gateway:
        fixtures.mongo.remove_document(
            fixtures.config.ums_db_name,
            fixtures.config.ums_users_collection,
            {"ext_id": sub},
        )
        if sub in registered_users:
            del registered_users[sub]
            fixtures.state.set_state("registered users", registered_users)
    assert sub not in registered_users


@when(
    parse('"{full_name}" retrieves their user data'),
    target_fixture="response",
)
def user_fetches_own_info(full_name: str, fixtures: JointFixture):
    """Fetches the user data for the given user from the UMS.

    Use session authentication if exist otherwise no authentication.
    """
    sub = fixtures.auth.get_sub(full_name)
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    headers = fixtures.auth.headers(session=session)
    user_id = session.user_id if session else sub
    url = f"{fixtures.config.ums_url}/users/{user_id}"
    return fixtures.http.get(url, headers=headers)


@when(parse('"{full_name}" registers as a new user'), target_fixture="response")
def user_registers(full_name: str, fixtures: JointFixture):
    title, name = fixtures.auth.split_title(full_name)
    email = fixtures.auth.get_email(name)
    sub = fixtures.auth.get_sub(name)
    user_data = {
        "name": name,
        "title": title,
        "email": email,
        "ext_id": sub,
    }
    url = f"{fixtures.config.ums_url}/users"
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    headers = fixtures.auth.headers(session=session)
    return fixtures.http.post(url, json=user_data, headers=headers)


@then(parse('the user data of "{full_name}" is returned'))
def user_gets_id(full_name: str, fixtures: JointFixture, response: Response):
    title, name = fixtures.auth.split_title(full_name)
    email = fixtures.auth.get_email(full_name)
    sub = fixtures.auth.get_sub(full_name)
    user = response.json()
    assert isinstance(user, dict)
    user_id = user["id"]
    assert user_id and "-" in user_id and len(user_id) > 6 and "@" not in user_id
    assert user["name"] == name
    assert user["title"] == title
    assert user["email"] == email
    assert user["ext_id"] == sub
    assert user["status"] == "active"
    registration_date = user.get("registration_date")
    assert registration_date and isinstance(registration_date, str)
    registration_date = registration_date.replace("Z", "+00:00")
    # the data steward has been pre-registered when the test bed first started,
    # but other users should have registered only when this test was running
    registration_timedelta = timedelta(
        seconds=60 * 60 * 24 * 365 if name == "Data Steward" else 60
    )
    assert (
        now_as_utc() - registration_timedelta
        < datetime.fromisoformat(registration_date)
        <= now_as_utc()
    )
    registered_users = fixtures.state.get_state("registered users") or {}
    registered_users[sub] = user_id
    fixtures.state.set_state("registered users", registered_users)


@given(parse('I lost my TOTP token as "{full_name}"'))
def totp_token_is_lost(full_name: str, fixtures: JointFixture):
    sub = fixtures.auth.get_sub(full_name)
    token = fixtures.state.get_state(f"totp-token-{sub}")
    assert not token, f"TOTP token for {full_name} should not exist"


@when(
    parse('I retrieve a new TOTP token as "{full_name}"'),
    target_fixture="new_totp_token",
)
def get_new_totp_token(full_name: str, fixtures: JointFixture):
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, "User session not found"
    assert session.user_id, "User ID not found"
    session_headers = fixtures.auth.headers_for_session(session)
    totp_token = fixtures.auth.get_totp_token(
        name=session.name,
        headers=session_headers,
        state_store=fixtures.state,
        force=True,  # requesting a new one because the previous is lost
    )
    return totp_token


@then(parse('the new TOTP token for "{full_name}" is validated'))
def validate_new_token(full_name: str, new_totp_token: str, fixtures: JointFixture):
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    assert session.user_id, f"user_id is missing for {full_name}"
    session_headers = fixtures.auth.headers_for_session(session)
    totp = fixtures.auth.generate_totp(new_totp_token)
    response = fixtures.auth.verify_totp(session.user_id, totp, session_headers)
    assert response.status_code == 204, response.text
    sub = fixtures.auth.get_sub(full_name)
    token_state = fixtures.state.get_state(f"totp-token-{sub}")
    assert token_state == new_totp_token
