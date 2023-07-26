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
from pathlib import Path
from typing import Any, NamedTuple

import httpx
from pytest_bdd import (  # noqa: F401; pylint: disable=unused-import
    given,
    parsers,
    scenarios,
    then,
    when,
)

from fixtures import (  # noqa: F401; pylint: disable=unused-import
    Config,
    ConnectorFixture,
    DskFixture,
    JointFixture,
    KafkaFixture,
    MongoFixture,
    S3Fixture,
    auth_fixture,
    batch_file_fixture,
    config_fixture,
    connector_fixture,
    dsk_fixture,
    joint_fixture,
    kafka_fixture,
    mongo_fixture,
    s3_fixture,
)

ARS_DB_NAME = "ars"
ARS_URL = "http://ars:8080"
AUTH_DB_NAME = "auth"
AUTH_USERS_COLLECTION = "users"
WPS_DB_NAME = "wps"
WPS_URL = "http://wps:8080"
DSK_TOKEN_PATH = Path.home() / ".ghga_data_steward_token.txt"  # path required by DSKit
IFRS_DB_NAME = "ifrs"
IFRS_METADATA_COLLECTION = "file_metadata"
METLDATA_DB_NAME = "metldata"

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


# Shared fixtures


class LoginFixture(NamedTuple):
    """A fixture to hold the users and their access tokens."""

    user: dict[str, Any]
    headers: dict[str, str]


# Shared step functions


@given(parse('I am logged in as "{name}"'), target_fixture="login")
def access_as_user(name: str, fixtures: JointFixture) -> LoginFixture:
    # Create user dictionary
    if name.startswith(("Prof. ", "Dr. ")):
        title, name = name.split(None, 1)
    else:
        title = None
    user_id = "id-of-" + name.lower().replace(" ", "-")
    ext_id = f"{user_id}@lifescience-ri.eu"
    email = name.lower().replace(" ", ".") + "@home.org"
    role = "data_steward" if "steward" in name.lower() else None
    user: dict[str, Any] = {
        "_id": user_id,
        "status": "active",
        "name": name,
        "email": email,
        "title": title,
        "ext_id": ext_id,
        "registration_date": 1688472000,
    }
    # Add the user to the auth database. This is needed
    # because users are not registered as part of the test.
    fixtures.mongo.replace_document(AUTH_DB_NAME, AUTH_USERS_COLLECTION, user)
    headers = fixtures.auth.generate_headers(
        id_=user_id, name=name, email=email, title=title, role=role
    )
    return LoginFixture(user, headers)


@then(parse('the response status code is "{code:d}"'))
def check_status_code(code: int, response: httpx.Response):
    assert response.status_code == code


# Global test bed state memory


@given("we start on a clean slate", target_fixture="state")
@async_step
async def reset_state(fixtures: JointFixture):
    await fixtures.s3.empty_buckets()  # empty object storage
    fixtures.kafka.delete_topics()  # empty event queues
    fixtures.mongo.empty_databases("tb")  # emtpy state database
    fixtures.mongo.empty_databases()  # empty service databases
    fixtures.dsk.reset_work_dir()  # reset local submission registry


@given(parse('we have the state "{name}"'), target_fixture="state")
def assume_state_clause(name: str, mongo: MongoFixture):
    value = get_state(name, mongo)
    assert value, f'The expected state "{name}" has not yet been set.'
    return value


@then(parse('set the state to "{name}"'))
def set_state_clause(name: str, mongo: MongoFixture):
    set_state(name, True, mongo)


def get_state(state_name: str, mongo: MongoFixture) -> Any:
    state = mongo.find_document("tb", "state", {"_id": state_name})
    return (state or {}).get("value")


def set_state(state_name: str, value: Any, mongo: MongoFixture):
    mongo.replace_document("tb", "state", {"_id": state_name, "value": value})


def unset_state(state_regex: str, mongo: MongoFixture):
    mongo.remove_document("tb", "state", {"_id": {"$regex": state_regex}})
