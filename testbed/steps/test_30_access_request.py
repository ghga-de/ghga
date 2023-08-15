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

"""Step definitions for access request tests"""

from datetime import timedelta
from time import sleep

import httpx
from ghga_service_commons.utils.utc_dates import now_as_utc

from fixtures.mongo import INTERVAL

from .conftest import (
    TIMEOUT,
    Config,
    LoginFixture,
    MongoFixture,
    given,
    parse,
    scenarios,
    then,
    unset_state,
    when,
)

scenarios("../features/30_access_request.feature")


def get_accession_for_dataset(
    dataset_char: str, config: Config, mongo: MongoFixture
) -> str:
    """Get the accession for the given dataset name"""
    # Get accession for the dataset
    # TBD: The accessions should actually be stored as state
    # in step2 where we are browsing the database
    # (at least in the black box testing mode)
    dataset = mongo.find_document(
        config.wps_db_name,
        "datasets",
        {"title": f"The complete-{dataset_char} dataset"},
    )
    assert dataset
    accession = dataset.get("_id")
    assert isinstance(accession, str)
    return accession


@given("no access requests have been made yet")
def ars_database_is_empty(config: Config, mongo: MongoFixture):
    mongo.empty_databases(config.ars_db_name)
    unset_state("is allowed to download", mongo)


@given("the claims repository is empty")
def claims_repository_is_empty(config: Config, mongo: MongoFixture):
    mongo.empty_databases(config.auth_db_name)


@when(
    parse('I request access to the test dataset "{dataset_char}"'),
    target_fixture="response",
)
def request_access_for_dataset(
    dataset_char: str, config: Config, login: LoginFixture, mongo: MongoFixture
):
    accession = get_accession_for_dataset(dataset_char, config, mongo)
    url = f"{config.ars_url}/access-requests"
    date_now = now_as_utc()
    user, headers = login
    data = {
        "user_id": user["_id"],
        "dataset_id": accession,
        "email": user["email"],
        "request_text": "Can I access the test dataset?",
        "access_starts": date_now.isoformat(),
        "access_ends": (date_now + timedelta(days=365)).isoformat(),
    }
    response = httpx.post(url, headers=headers, json=data)
    return response


@then(parse('an email has been sent to "{email}"'))
def check_email_sent_to(
    config: Config, email: str, timeout: float = TIMEOUT, interval: float = INTERVAL
):
    """Validate e-mail notification.

    Wait for an e-mail to be received by the mail server. If it does not appear
    within the given timeout (in seconds), an AssertionError is raised.
    """

    url = f"{config.mailhog_url}/api/v2/search"
    slept: float = 0
    while slept < timeout:
        response = httpx.get(
            url,
            headers={"accept": "application/json"},
            params={"kind": "to", "query": email},
            timeout=TIMEOUT,
        )
        assert response.status_code == 200
        if response.json()["count"] > 0:
            return
        sleep(interval)
        slept += interval
    assert False, f"An email notification was not received by {email}."


@when("I fetch the list of access requests", target_fixture="response")
def fetch_list_of_access_requests(config: Config, login: LoginFixture):
    url = f"{config.ars_url}/access-requests"
    response = httpx.get(url, headers=login.headers, timeout=TIMEOUT)
    return response


@then(parse('there is one request for test dataset "{dataset_char}" from "{name}"'))
def there_is_one_request(
    dataset_char: str,
    name: str,
    config: Config,
    mongo: MongoFixture,
    response: httpx.Response,
):
    accession = get_accession_for_dataset(dataset_char, config, mongo)
    requests = response.json()
    requests = [
        request
        for request in requests
        if request["dataset_id"] == accession and request["full_user_name"] == name
    ]
    assert len(requests) == 1


@when(parse('I allow the pending request from "{name}"'), target_fixture="response")
def allow_pending_request(
    config: Config, name: str, login: LoginFixture, response: httpx.Response
):
    requests = response.json()
    requests = [
        request
        for request in requests
        if request["status"] == "pending" and request["full_user_name"] == name
    ]
    assert len(requests) == 1
    request = requests[0]
    request_id = request["id"]
    url = f"{config.ars_url}/access-requests/{request_id}"
    data = {"status": "allowed"}
    response = httpx.patch(url, headers=login.headers, json=data)
    return response


@then(parse('the status of the request from "{name}" is "{status}"'))
def there_are_access_requests(name: str, status: str, response: httpx.Response):
    requests = response.json()
    requests = [request for request in requests if request["full_user_name"] == name]
    assert len(requests) == 1
    request = requests[0]
    assert request["status"] == status
