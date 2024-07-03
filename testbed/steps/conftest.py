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
    StateStorage,
    VaultFixture,
    auth_fixture,
    batch_file_fixture,
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
    vault_fixture,
)
from pytest_bdd import (  # noqa: RUF100
    given,
    parsers,
    scenarios,
    then,
    when,
)

from steps.utils import EXPECTED_NOTIFICATIONS, parse_notifications

parse = parsers.parse  # pylint: disable=invalid-name

# Helpers for async step functions


def async_step(step):
    """Decorator that converts an async step function to a normal one."""
    signature = inspect.signature(step)
    parameters = list(signature.parameters.values())
    has_event_loop = any(parameter.name == "event_loop" for parameter in parameters)
    if not has_event_loop:
        parameters.append(
            inspect.Parameter("event_loop", inspect.Parameter.POSITIONAL_OR_KEYWORD)
        )
        step.__signature__ = signature.replace(parameters=parameters)

    @wraps(step)
    def run_step(*args, **kwargs):
        loop = kwargs["event_loop"] if has_event_loop else kwargs.pop("event_loop")
        return loop.run_until_complete(step(*args, **kwargs))

    return run_step


# Shared step functions


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
def access_as_user(name: str, fixtures: JointFixture):
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


def fetch_data_stewardship(fixtures: JointFixture) -> tuple[Any, Any]:
    """Fetch the data steward and the corresponding claim from the database."""
    assert not fixtures.config.use_api_gateway
    data_steward_claim = fixtures.mongo.find_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_claims_collection,
        {"visa_value": "data_steward@ghga.de"},
    )
    data_steward = (
        fixtures.mongo.find_document(
            fixtures.config.ums_db_name,
            fixtures.config.ums_users_collection,
            {"_id": data_steward_claim["user_id"]},
        )
        if data_steward_claim
        else None
    )
    return data_steward, data_steward_claim


def restore_data_stewardship(state: tuple[Any, Any], fixtures: JointFixture) -> None:
    """Put the data steward and the corresponding claim back into the database."""
    assert not fixtures.config.use_api_gateway
    data_steward, data_steward_claim = state
    if data_steward:
        fixtures.mongo.replace_document(
            fixtures.config.ums_db_name,
            fixtures.config.ums_users_collection,
            data_steward,
        )
    if data_steward_claim:
        fixtures.mongo.replace_document(
            fixtures.config.ums_db_name,
            fixtures.config.ums_claims_collection,
            data_steward_claim,
        )


@given("we start on a clean slate")
@async_step
async def reset_state(fixtures: JointFixture):
    """Reset all state used by the Archive Test Bed."""
    fixtures.state.reset_state()  # empty state database
    if not fixtures.config.use_api_gateway:
        # When running the tests externally using the API gateway,
        # we do not have access permissions to the state databases,
        # so we rely on the deployment to start with a clean slate.
        await fixtures.s3.empty_buckets()  # empty object storage
        await fixtures.kafka.delete_topics()  # remove event queues
        saved_data_steward = fetch_data_stewardship(fixtures)
        fixtures.mongo.empty_databases()  # empty service databases
        restore_data_stewardship(saved_data_steward, fixtures)
    fixtures.dsk.reset_work_dir()  # reset local submission registry
    empty_mail_server(fixtures)  # reset mail server


@given("no notification has been sent yet")
@async_step
async def reset_notifications(fixtures: JointFixture):
    """Delete all email notifications from the mail server."""
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


@then(parse('the expected hit count is "{count:d}"'))
def check_hit_count(count: int, response: Response):
    results = response.json()
    assert results["count"] == count


@then(parse('I receive "{item_count:d}" item'))
@then(parse('I receive "{item_count:d}" items'))
def check_received_item_count(response: Response, item_count):
    results = response.json()
    assert len(results["hits"]) == item_count


@then(parse('the expected item count is "{expected_count:d}"'))
def check_item_count_in_list(results: list, expected_count):
    assert len(results) == expected_count


@then(parse('"{notification_type}" notification was sent to "{full_name}"'))
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
    email = fixtures.auth.get_email(full_name)
    if notification_type != "account_details_changed":
        # When the registered email changes, notification is sent to the original email
        sub = fixtures.auth.get_sub(full_name)
        all_changed_user_data = fixtures.state.get_state("changed user data") or {}
        changed_user_data = all_changed_user_data.get(sub) or {}
        email = changed_user_data.get("email", email)
    assert subject, f"Undefined notification type: {notification_type}"
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
            return
        sleep(interval)
        slept += interval
    assert False, f"An email notification was not received by {email}."
