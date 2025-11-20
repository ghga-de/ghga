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

scenarios("../features/320_access_request.feature")


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
    parse('"{full_name}" updates "{field}" of the request to "{value}"'),
    target_fixture="response",
)
def update_access_request(
    full_name: str, field: str, value: str, fixtures: JointFixture, requests
):
    assert len(requests) == 1
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    headers = fixtures.auth.headers(session=session)
    assert session
    field_key = field.lower().replace(" ", "_")
    data = {field_key: value}
    access_request_id = requests[0]["id"]
    url = f"{fixtures.config.ars_url}/access-requests/{access_request_id}"
    return fixtures.http.patch(url, headers=headers, json=data)


@when(
    parse('"{full_name}" fetches the list of access requests for "{alias}"'),
    target_fixture="response",
)
def fetch_access_requests(fixtures: JointFixture, full_name: str, alias: str | None):
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    headers = fixtures.auth.headers(session=session)
    url = f"{fixtures.config.ars_url}/access-requests"

    params = {}
    if alias and alias != "all":
        datasets = fixtures.state.get_state("all available datasets")
        assert alias in datasets
        dataset_id = datasets[alias]["accession"]
        params["dataset_id"] = dataset_id
    return fixtures.http.get(url, headers=headers, params=params)


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
    parse('"{approver_name}" allows the pending requests from "{requester_name}"'),
    target_fixture="allowed_requests",
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
    assert len(requests) == 2  # both for DS_A and DS_B
    for request in requests:
        request_id = request["id"]
        url = f"{fixtures.config.ars_url}/access-requests/{request_id}"
        data = {"status": "allowed"}
        response = fixtures.http.patch(url, headers=headers, json=data)
        assert response.status_code == 204
    return requests


@then("the user have access to the two test datasets")
def user_has_access_to_datasets(fixtures: JointFixture, allowed_requests):
    assert len(allowed_requests) == 2
    available_datasets = fixtures.state.get_state("all available datasets")
    requested_datasets = [request["dataset_id"] for request in allowed_requests]
    datasets_with_access = {
        alias: dataset["accession"]
        for alias, dataset in available_datasets.items()
        if dataset["accession"] in requested_datasets
    }
    fixtures.state.set_state("datasets users can access", datasets_with_access)


@then(parse('the "{field}" of the request for dataset "{alias}" is "{value}"'))
def there_are_access_requests(
    field: str, alias: str, value: str, fixtures: JointFixture, requests
):
    datasets = fixtures.state.get_state("all available datasets")
    field = field.lower().replace(" ", "_")
    assert alias in datasets
    dataset_id = datasets[alias]["accession"]
    requests = [request for request in requests if request["dataset_id"] == dataset_id]
    assert len(requests) == 1
    request = requests[0]
    assert request[field] == value
