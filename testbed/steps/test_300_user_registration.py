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

from steps.utils import reset_user_token_counter

from .conftest import (
    JointFixture,
    Response,
    given,
    parse,
    scenarios,
    then,
    when,
)

scenarios("../features/300_user_registration.feature")


@given(parse('the user "{full_name}" is not yet registered'))
def user_not_yet_registered(full_name: str, fixtures: JointFixture):
    registered_users = fixtures.state.get_state("registered users") or {}
    sub = fixtures.auth.get_sub(full_name)
    fixtures.mongo.remove_documents(
        fixtures.config.ums_db_name,
        fixtures.config.ums_users_collection,
        {"ext_id": sub},
    )
    if sub in registered_users:
        del registered_users[sub]
        fixtures.state.set_state("registered users", registered_users)
    assert sub not in registered_users
    changed_user_data = fixtures.state.get_state("changed user data") or {}
    if sub in changed_user_data:
        del changed_user_data[sub]
        fixtures.state.set_state("changed user data", changed_user_data)


@when(parse('"{full_name}" registers as a new user'), target_fixture="response")
def user_registers(full_name: str, fixtures: JointFixture):
    auth = fixtures.auth
    title, name = auth.split_title(full_name)
    email = auth.get_email(name)
    sub = auth.get_sub(name)
    user_data = {
        "name": name,
        "title": title,
        "email": email,
        "ext_id": sub,
    }
    url = f"{fixtures.config.ums_url}/users"
    session = auth.get_saved_session(name=full_name, state_store=fixtures.state)
    headers = auth.headers(session=session)
    return fixtures.http.post(url, json=user_data, headers=headers)


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
    session_headers = fixtures.auth.headers(session)
    totp_token = fixtures.auth.get_totp_token(
        name=session.name,
        headers=session_headers,
        state_store=fixtures.state,
        force=True,  # requesting a new one because the previous is lost
    )
    return totp_token


@then(parse('the session state is "{state}"'))
def check_session_state(state: str, fixtures: JointFixture):
    sub = fixtures.state.get_state("logged in as")
    assert sub
    session = fixtures.state.get_state(f"session-{sub}")
    assert session
    assert session["state"] == state


@then(parse('I get the error "{detail}"'))
def check_token_error(detail: str, new_totp_token: str):
    assert new_totp_token == f"error: {detail}"


@then(parse('the new TOTP token for "{full_name}" is validated'))
def validate_new_token(full_name: str, new_totp_token: str, fixtures: JointFixture):
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    assert session.user_id, f"user_id is missing for {full_name}"
    session_headers = fixtures.auth.headers(session)
    totp = fixtures.auth.generate_totp(new_totp_token)
    response = fixtures.auth.verify_totp(totp, session_headers)
    assert response.status_code == 204, response.text
    sub = fixtures.auth.get_sub(full_name)
    token_state = fixtures.state.get_state(f"totp-token-{sub}")
    assert token_state == new_totp_token


@given(parse('"{full_name}" has {a_new_or_the_old} email address'))
def new_email_address(full_name: str, a_new_or_the_old: str, fixtures: JointFixture):
    all_changed_user_data = fixtures.state.get_state("changed user data") or {}
    sub = fixtures.auth.get_sub(full_name)
    changed_user_data = all_changed_user_data.setdefault(sub, {})
    if "new" in a_new_or_the_old:
        email = fixtures.auth.get_email(full_name)
        changed_user_data["email"] = email.replace("@home", "@new-home")
    else:
        if "email" in changed_user_data:
            del changed_user_data["email"]
    fixtures.state.set_state("changed user data", all_changed_user_data)


@when(
    parse('"{full_name}" re-registers with the {old_or_new} email'),
    target_fixture="response",
)
def user_re_registers(full_name: str, old_or_new: str, fixtures: JointFixture):
    auth = fixtures.auth
    title, name = auth.split_title(full_name)
    email = auth.get_email(name)
    if old_or_new == "new":
        email = email.replace("@home", "@new-home")
    user_data = {
        "name": name,
        "title": title,
        "email": email,
    }
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session
    user_id = session.user_id
    assert user_id
    url = f"{fixtures.config.ums_url}/users/{user_id}"
    headers = auth.headers(session=session)
    return fixtures.http.put(url, json=user_data, headers=headers)


@when(
    parse('"{full_name}" changes the title to "{title}"'),
    target_fixture="response",
)
def user_changes_title(full_name: str, title: str, fixtures: JointFixture):
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session
    user_id = session.user_id
    assert user_id
    url = f"{fixtures.config.ums_url}/users/{user_id}"
    headers = fixtures.auth.headers(session=session)
    user_data = {"title": title}
    response = fixtures.http.patch(url, json=user_data, headers=headers)
    if response.status_code == 204:
        all_changed_user_data = fixtures.state.get_state("changed user data") or {}
        sub = fixtures.auth.get_sub(full_name)
        changed_user_data = all_changed_user_data.setdefault(sub, {})
        changed_user_data["title"] = title
        fixtures.state.set_state("changed user data", all_changed_user_data)
    return response


@when(
    parse('"{full_name}" retrieves the user data of "{other_full_name}"'),
    target_fixture="response",
)
def user_retrieve_user_data(
    full_name: str, other_full_name: str, fixtures: JointFixture
):
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session

    registered_users = fixtures.state.get_state("registered users") or {}
    other_user_sub = fixtures.auth.get_sub(other_full_name)
    other_user_id = registered_users.get(other_user_sub)

    url = f"{fixtures.config.ums_url}/users/{other_user_id}"
    headers = fixtures.auth.headers(session=session)
    return fixtures.http.get(url, headers=headers)


@given(parse('the state of "{full_name}" IVA is "{state}"'))
def set_iva_state(full_name: str, state: str, fixtures: JointFixture):
    """Retrieve the list of all IVAs and delete them"""
    registered_users = fixtures.state.get_state("registered users") or {}
    user_sub = fixtures.auth.get_sub(full_name)
    user_id = registered_users.get(user_sub)

    iva = fixtures.mongo.find_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_user_ivas_collection,
        query={"user_id": user_id},
    )
    assert iva
    iva["state"] = state

    # Overwrite the IVA state in Mongo directly
    fixtures.mongo.upsert_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_user_ivas_collection,
        iva,
    )

    # Make sure the document is updated before
    document = fixtures.mongo.wait_for_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_user_ivas_collection,
        query={"user_id": user_id, "state": state},
    )
    assert document
