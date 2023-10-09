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

"""Shared steps and fixtures"""

import inspect
from functools import wraps
from typing import Any, NamedTuple, Optional

import httpx
from fixtures import (  # noqa: RUF100
    Config,
    ConnectorFixture,
    DskFixture,
    JointFixture,
    KafkaFixture,
    MongoFixture,
    S3Fixture,
    StateStorage,
    auth_fixture,
    batch_file_fixture,
    config_fixture,
    connector_fixture,
    dsk_fixture,
    event_loop,
    file_fixture,
    joint_fixture,
    kafka_fixture,
    mongo_fixture,
    s3_fixture,
    state_fixture,
)
from pytest_bdd import (  # noqa: RUF100
    given,
    parsers,
    scenarios,
    then,
    when,
)

TIMEOUT = 10

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
    title: Optional[str]
    email: str


class LoginFixture(NamedTuple):
    """A fixture to hold a user and a corresponding access token."""

    user: UserData
    headers: dict[str, str]


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


@given(parse('I am logged in as "{name}"'), target_fixture="login")
def access_as_user(name: str, fixtures: JointFixture) -> LoginFixture:
    user = get_user_data(name, fixtures)
    headers = fixtures.auth.generate_headers(name=name, user_id=user.id)
    return LoginFixture(user, headers)


@then(parse('the response status code is "{code:d}"'))
def check_status_code(code: int, response: httpx.Response):
    assert response.status_code == code


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
        fixtures.kafka.delete_topics()  # empty event queues
        saved_data_steward = fetch_data_stewardship(fixtures)
        fixtures.mongo.empty_databases()  # empty service databases
        restore_data_stewardship(saved_data_steward, fixtures)
    fixtures.dsk.reset_work_dir()  # reset local submission registry
    empty_mail_server(fixtures.config)  # reset mail server


@given(parse('we have the state "{name}"'))
def assume_state_clause(name: str, state: StateStorage):
    value = state.get_state(name)
    assert value, f'The expected state "{name}" has not yet been set.'
    return value


@then(parse('set the state to "{name}"'))
def set_state_clause(name: str, state: StateStorage):
    state.set_state(name, True)


def empty_mail_server(config: Config):
    """Delete all e-mails from mail server"""
    httpx.delete(f"{config.mailhog_url}/api/v1/messages", timeout=TIMEOUT)


@then(parse('the expected hit count is "{count:d}"'))
def check_hit_count(count: int, response: httpx.Response):
    results = response.json()
    assert results["count"] == count


@then(parse('I receive "{item_count:d}" item'))
@then(parse('I receive "{item_count:d}" items'))
def check_received_item_count(response: httpx.Response, item_count):
    results = response.json()
    assert len(results["hits"]) == item_count
