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

"""Step definitions for requesting access in the frontend"""

from datetime import UTC, datetime, timedelta
from time import sleep

from ghga_service_commons.utils.utc_dates import now_as_utc

from .conftest import (
    JointFixture,
    Response,
    StateStorage,
    fetch_data_stewardship,
    given,
    parse,
    restore_data_stewardship,
    scenarios,
    then,
    when,
)

scenarios("../features/32_access_request.feature")


@given("no access requests have been made yet")
def ars_database_is_empty(fixtures: JointFixture):
    if fixtures.config.use_api_gateway:
        # black-box testing: cannot empty service database
        assert not fixtures.state.get_state("is allowed to download")
        return
    fixtures.mongo.empty_databases(fixtures.config.ars_db_name)
    fixtures.state.unset_state("is allowed to download")


@given("the claims repository is empty")
def claims_repository_is_empty(fixtures: JointFixture):
    """Remove all claims except for the data steward claim."""
    if fixtures.config.use_api_gateway:
        # black-box testing: cannot empty service database
        return
    saved_data_steward = fetch_data_stewardship(fixtures)
    fixtures.mongo.empty_databases(
        fixtures.config.ums_db_name,
        exclude_collections=[
            fixtures.config.ums_users_collection,
            fixtures.config.ums_user_tokens_collection,
            fixtures.config.ums_user_ivas_collection,
        ],
    )
    restore_data_stewardship(saved_data_steward, fixtures)


@when(
    parse('"{full_name}" requests access to the test dataset "{alias}"'),
    target_fixture="response",
)
def request_access_for_dataset(full_name: str, alias: str, fixtures: JointFixture):
    iva = fixtures.state.get_state("iva")
    assert iva["id"]
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session
    headers = fixtures.auth.headers(session=session)
    datasets = fixtures.state.get_state("all available datasets")
    assert alias in datasets
    dataset_id = datasets[alias]["accession"]
    url = f"{fixtures.config.ars_url}/access-requests"
    date_now = now_as_utc()
    data = {
        "user_id": session.user_id,
        "iva_id": iva["id"],
        "dataset_id": dataset_id,
        "email": session.email,
        "request_text": "Can I access the test dataset?",
        "access_starts": date_now.isoformat(),
        "access_ends": (date_now + timedelta(days=365)).isoformat(),
    }

    return fixtures.http.post(url, headers=headers, json=data)


@when(
    parse('"{full_name}" fetches the list of access requests'),
    target_fixture="response",
)
def fetch_list_of_access_requests(fixtures: JointFixture, full_name: str):
    url = f"{fixtures.config.ars_url}/access-requests"
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    headers = fixtures.auth.headers(session=session)
    return fixtures.http.get(url, headers=headers)


@then(
    parse('there is one request for test dataset "{alias}" from "{name}"'),
    target_fixture="requests",
)
def there_is_one_request(
    alias: str,
    name: str,
    state: StateStorage,
    response: Response,
):
    datasets = state.get_state("all available datasets")
    assert alias in datasets
    dataset_id = datasets[alias]["accession"]
    requests = response.json()
    requests = [
        request
        for request in requests
        if request["dataset_id"] == dataset_id and request["full_user_name"] == name
    ]
    assert len(requests) == 1
    return requests


@when(
    parse('"{approver_name}" allows the pending request from "{requester_name}"'),
    target_fixture="response",
)
def allow_pending_request(
    approver_name: str, requester_name: str, fixtures: JointFixture
):
    url = f"{fixtures.config.ars_url}/access-requests"
    session = fixtures.auth.get_saved_session(
        name=approver_name, state_store=fixtures.state
    )
    headers = fixtures.auth.headers(session=session)
    response = fixtures.http.get(url, headers=headers)
    assert response.status_code == 200
    requests = response.json()
    requests = [
        request
        for request in requests
        if request["status"] == "pending"
        and request["full_user_name"] == requester_name
    ]
    assert len(requests) == 1
    request = requests[0]
    request_id = request["id"]
    url = f"{fixtures.config.ars_url}/access-requests/{request_id}"
    data = {"status": "allowed"}
    return fixtures.http.patch(url, headers=headers, json=data)


@then(parse('the status of the request from "{name}" is "{status}"'))
def there_are_access_requests(name: str, status: str, requests):
    requests = [request for request in requests if request["full_user_name"] == name]
    assert len(requests) == 1
    request = requests[0]
    assert request["status"] == status
