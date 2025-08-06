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
#

"""Shared steps and fixtures"""

import inspect
from functools import wraps
from time import sleep
from typing import Any, NamedTuple

from fixtures import (  # noqa: RUF100
    Config,
    ConnectorFixture,
    DskFixture,
    HttpClient,
    JointFixture,
    KafkaFixture,
    MongoFixture,
    Response,
    S3Fixture,
    StateManager,
    StateStorage,
    VaultFixture,
    auth_fixture,
    config_fixture,
    connector_fixture,
    dsk_fixture,
    file_fixture,
    http_fixture,
    iva_fixture,
    joint_fixture,
    kafka_fixture,
    mongo_fixture,
    s3_fixture,
    state_fixture,
    state_manager_fixture,
    vault_fixture,
)
from pytest import mark
from pytest_bdd import (  # noqa: RUF100
    given,
    scenarios,
    then,
    when,
)

from steps.conftest_3x import *  # noqa: F403
from steps.conftest_3x import parse
from steps.utils import (
    EXPECTED_NOTIFICATIONS,
    parse_notifications,
    reset_user_token_counter,
)


class UserData(NamedTuple):
    """A container for user data."""

    id: str
    ext_id: str
    name: str
    title: str | None
    email: str


def get_user_data(name: str, fixtures: JointFixture) -> UserData:
    auth = fixtures.auth
    title, name = auth.split_title(name)
    sub = auth.get_sub(name)
    registered_users = fixtures.state.get_state("registered users") or {}
    user_id = registered_users.get(sub)
    assert user_id, f"{name} is not a registered user"
    email = auth.get_email(name)
    return UserData(user_id, sub, name, title, email)


@given(parse('I am registered as "{name}"'), target_fixture="user")
def registered_as_user(name: str, fixtures: JointFixture) -> UserData:
    return get_user_data(name, fixtures)


@given(parse('I am logged in as "{name}"'))
def login_as_user(name: str, fixtures: JointFixture):
    sub = fixtures.auth.get_sub(name)
    session = fixtures.auth.fetch_session(
        name=name, user_id=sub, state_store=fixtures.state
    )
    fixtures.auth.save_session(name=name, session=session, state_store=fixtures.state)


@given(parse('I am authenticated as "{full_name}"'))
def authenticate_user(full_name: str, fixtures: JointFixture):
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    response = fixtures.auth.authenticate(session=session, state_store=fixtures.state)
    assert response.status_code == 204, response.text

    # Update session cache with up-to-date session information from server
    login_as_user(full_name, fixtures)


@given(parse('the user "{name}" is logged out'))
def logout_as_user(name: str, fixtures: JointFixture):
    """Log out the user without knowing the login status on server.

    Sessions that are alive in the Auth Adapter need to be removed.
    In order to achieve this, the session is retrieved via login and used to logout.
    """
    sub = fixtures.auth.get_sub(name)
    session = fixtures.auth.get_saved_session(name=name, state_store=fixtures.state)
    if not session:
        print("No session found, creating a new one.")
        session = fixtures.auth.fetch_session(name=name, user_id=sub)
    reset_user_token_counter(sub, fixtures)
    fixtures.auth.auth_logout(session)
    fixtures.state.unset_state(f"session-{sub}")


@then(parse('the response status code is "{code:d}"'))
def check_status_code(code: int, response: Response):
    status_code = response.status_code
    assert status_code == code, f"{status_code}: {response.text}"


@given("the session store is empty")
def empty_session_store(fixtures: JointFixture):
    """Remove all states starting with "session" from the state storage"""
    fixtures.state.unset_state("session")


@given("the TOTP token store is empty")
def empty_totp_token_store(fixtures: JointFixture):
    """Remove all states starting with "totp-token" from the state storage"""
    fixtures.state.unset_state("totp-token-")


# Global test bed state memory


def fetch_data_stewardship(fixtures: JointFixture) -> dict[str, Any]:
    """Fetch the data steward and the corresponding claim from the database."""
    state = {}
    claim = fixtures.mongo.find_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_claims_collection,
        {"visa_value": "data_steward@ghga.de"},
    )
    assert claim is not None, "no data steward claim found in the auth database"
    state["claim"] = claim
    user_id = claim["user_id"]
    user = fixtures.mongo.find_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_users_collection,
        {"_id": user_id},
    )
    assert user is not None, "no data steward found in the auth database"
    state["user"] = user
    user = fixtures.mongo.find_document(
        fixtures.config.nos_db_name,
        "users",
        {"_id": user_id},
    )
    assert user is not None, "no data steward found in the nos database"
    state["nos"] = user
    iva = fixtures.mongo.find_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_user_ivas_collection,
        {"user_id": user_id},
    )
    assert iva is not None, "no data steward IVA in the ums database"
    state["iva"] = iva
    return state


def restore_data_stewardship(state: dict[str, Any], fixtures: JointFixture) -> None:
    """Put the data steward and the corresponding claim back into the database."""
    user = state["user"]
    assert user
    fixtures.mongo.upsert_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_users_collection,
        user,
    )
    user = state["nos"]
    assert user
    fixtures.mongo.upsert_document(
        fixtures.config.nos_db_name,
        "users",
        user,
    )
    claim = state.get("claim")
    assert claim
    fixtures.mongo.upsert_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_claims_collection,
        claim,
    )
    iva = state.get("iva")
    assert iva
    fixtures.mongo.upsert_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_user_ivas_collection,
        iva,
    )
    registered_users = fixtures.state.get_state("registered users") or {}
    registered_users[state["user"]["ext_id"]] = state["user"]["_id"]
    fixtures.state.set_state("registered users", registered_users)


@given("we start on a clean slate")
def reset_state(fixtures: JointFixture):
    """Reset all state used by the Archive Test Bed."""
    fixtures.state.reset_state()  # empty state database
    fixtures.kafka.clear_topics()  # empty event queues
    fixtures.s3.empty_buckets()  # empty object storages
    saved_data_steward = fetch_data_stewardship(fixtures)
    fixtures.mongo.empty_databases()  # empty service databases
    restore_data_stewardship(saved_data_steward, fixtures)
    fixtures.dsk.reset_work_dir()  # reset local submission registry
    empty_mail_server(fixtures)  # reset mail server
    if not fixtures.config.black_box_mode:
        fixtures.vault.empty_secrets()  # empty secret storage


@given("no notification has been sent yet")
def reset_notifications(fixtures: JointFixture):
    """Delete all email notifications from the mail server."""
    fixtures.mongo.empty_databases("ns")
    empty_mail_server(fixtures)  # reset mail server


@given(parse('we have the state "{name}"'))
def assume_state_clause(name: str, state: StateStorage):
    value = state.get_state(name)
    assert value, f'The expected state "{name}" has not yet been set.'
    return value


@then(parse('set the state to "{name}"'))
def set_state_clause(name: str, state: StateStorage):
    state.set_state(name, True)


@then(parse('remove the state "{name}"'))
def unset_state_clause(name: str, state: StateStorage):
    state.unset_state(name)


def empty_mail_server(fixtures: JointFixture):
    """Delete all e-mails from mail server"""
    fixtures.http.delete(f"{fixtures.config.mail_url}/api/v1/messages")


@then(parse('I get only dataset "{ega_accession}" as search result'))
def check_study_search_result(ega_accession: str, response: Response):
    results = response.json()
    assert results["count"] == 1
    assert results["hits"][0]["content"]["ega_accession"] == ega_accession


@then(parse('I get "{count:d}" search results'))
def check_number_of_search_results(count: int, response: Response):
    results = response.json()
    assert results["count"] == count
    assert len(results["hits"]) == count


@then(parse('I get "{page_count:d}" out of "{total_count:d}" search results'))
def check_number_of_search_results_on_the_page(
    page_count: int, total_count: int, response: Response
):
    results = response.json()
    assert results["count"] == total_count
    assert len(results["hits"]) == page_count


@then(parse('the expected item count is "{count:d}"'))
def check_item_count_in_list(count: int, results: list):
    assert len(results) == count


@then(parse('"{notification_type}" email was sent to "{full_name}"'))
def check_email_sent_to(
    notification_type: str,
    full_name: str,
    fixtures: JointFixture,
    timeout: float = 15,
    interval: float = 0.1,
):
    """Validate e-mail notification.

    Wait for an e-mail to be received by the mail server. If it does not appear
    within the given timeout (in seconds), an AssertionError is raised.
    """
    notification_type = notification_type.lower().replace(" ", "_")
    url = f"{fixtures.config.mail_url}/api/v2/search"
    slept: float = 0
    subject = EXPECTED_NOTIFICATIONS.get(notification_type)
    assert subject, f"Undefined notification type: {notification_type}"
    if "(" in full_name:
        full_name, note = full_name.split("(", 1)
        full_name, note = full_name.rstrip(), note.rstrip(")")
    else:
        note = ""
    email = fixtures.auth.get_email(full_name)
    if "new email" in note:
        email = email.replace("@home", "@new-home")
    while slept < timeout:
        response = fixtures.http.get(
            url,
            headers={"accept": "application/json"},
            params={"kind": "containing", "query": subject},
            timeout=timeout,
        )  # not possible to filter by email and subject at the same time
        assert response.status_code == 200
        content = response.json()
        if content["count"] > 0:
            notifications = parse_notifications(content)
            latest_notification = notifications[0]
            assert email in latest_notification.receiver
            assert latest_notification.is_recent()
            # delete the notification from the mail server as already seen
            url = f"{fixtures.config.mail_url}/api/v1/messages/{latest_notification.id}"
            response = fixtures.http.delete(url, timeout=timeout)
            assert response.status_code == 200
            return
        sleep(interval)
        slept += interval
    assert False, f"An email notification was not received by {email}."


@given("no file encryption secrets exist in the vault")
def reset_file_encryption_secrets(fixtures: JointFixture):
    """Reset the file encryption secrets in the vault."""
    if not fixtures.config.black_box_mode:
        fixtures.vault.empty_secrets()  # empty secret storage
