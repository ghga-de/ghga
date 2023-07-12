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

from typing import Any, NamedTuple

import httpx
from pytest_asyncio import fixture as async_fixture
from pytest_bdd import (  # noqa: F401; pylint: disable=unused-import
    given,
    parsers,
    scenarios,
    then,
    when,
)

from fixtures import (  # noqa: F401; pylint: disable=unused-import
    Config,
    JointFixture,
    MongoFixture,
    auth_fixture,
    batch_create_file_fixture,
    c4gh_fixture,
    config_fixture,
    joint_fixture,
    kafka_fixture,
    mongo_fixture,
    s3_fixture,
    submission_config_fixture,
    submission_workdir_fixture,
)

ARS_DB_NAME = "ars"
ARS_URL = "http://ars:8080"
AUTH_DB_NAME = "auth"
AUTH_USERS_COLLECTION = "users"
WPS_DB_NAME = "wps"
WPS_URL = "http://wps:8080"

TIMEOUT = 10

parse = parsers.parse  # pylint: disable=invalid-name


class LoginFixture(NamedTuple):
    """A fixture to hold the users and their access tokens."""

    user: dict[str, Any]
    headers: dict[str, str]


# shared step functions


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


@async_fixture
async def reset_buckets(fixtures: JointFixture):
    await fixtures.s3.empty_buckets()


@given("we start on a clean slate", target_fixture="state")
def reset_state(
    fixtures: JointFixture, reset_buckets
):  # pylint: disable=unused-argument
    fixtures.kafka.delete_topics()
    fixtures.mongo.empty_databases("tb")  # state database
    fixtures.mongo.empty_databases()  # service databases


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
