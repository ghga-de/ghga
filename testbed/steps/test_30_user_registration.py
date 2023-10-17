# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Step definitions for requesting access in the frontend"""

from datetime import datetime, timedelta

from ghga_service_commons.utils.utc_dates import now_as_utc

from .conftest import JointFixture, Response, given, parse, scenarios, then, when

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
    parse('the user "{full_name}" retrieves the own user data'),
    target_fixture="response",
)
def user_fetches_own_info(full_name: str, fixtures: JointFixture):
    sub = fixtures.auth.get_sub(full_name)
    url = f"{fixtures.config.ums_url}/users/{sub}"
    headers = fixtures.auth.generate_headers(full_name)
    return fixtures.http.get(url, headers=headers)


@when(parse('the user "{full_name}" tries to register'), target_fixture="response")
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
    headers = fixtures.auth.generate_headers(full_name)
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
