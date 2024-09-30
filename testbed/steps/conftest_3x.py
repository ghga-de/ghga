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

"""Shared test used for steps with prefix test_3*"""

from datetime import datetime, timedelta

from fixtures import (  # noqa: RUF100
    Config,
    ConnectorFixture,
    JointFixture,
    Response,
)
from ghga_service_commons.utils.utc_dates import now_as_utc
from pytest_bdd import (  # noqa: RUF100
    given,
    parsers,
    then,
    when,
)

parse: type[parsers.StepParser] = parsers.parse  # pylint: disable=invalid-name


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
    user_id = session.user_id if session else sub
    url = f"{fixtures.config.ums_url}/users/{user_id}"
    headers = fixtures.auth.headers(session)
    return fixtures.http.get(url, headers=headers)


@then(parse('the expected user data of "{full_name}" is returned'))
def user_gets_id(full_name: str, fixtures: JointFixture, response: Response):
    title, name = fixtures.auth.split_title(full_name)
    email = fixtures.auth.get_email(full_name)
    sub = fixtures.auth.get_sub(full_name)
    user = response.json()
    assert isinstance(user, dict)
    user_id = user["id"]
    assert user_id and "-" in user_id and len(user_id) > 6 and "@" not in user_id
    all_changed_user_data = fixtures.state.get_state("changed user data") or {}
    changed_user_data = all_changed_user_data.get(sub) or {}
    title = changed_user_data.get("title", title)
    email = changed_user_data.get("email", email)
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


@given("I have an empty working directory for the GHGA connector")
def clean_connector_work_dir(connector: ConnectorFixture):
    connector.reset_work_dir()


@given("my Crypt4GH key pair has been stored in two key files")
def keys_are_made_available(connector: ConnectorFixture, config: Config):
    connector.store_keys(
        public_key=config.user_public_crypt4gh_key,
        private_key=config.user_private_crypt4gh_key,
    )
