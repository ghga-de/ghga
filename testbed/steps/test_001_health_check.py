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

"""Step definition for service health check using health endpoint"""

from json import JSONDecodeError

from pytest_bdd import scenarios, then, when

from .conftest import Config, JointFixture

scenarios("../features/001_health_check.feature")


def check_api_is_healthy(api: str, fixtures: JointFixture):  # noqa: C901
    """Check that service API is healthy or not reachable if internal."""
    config = fixtures.config
    is_internal = api in config.internal_apis
    health_endpoint = getattr(config, f"{api}_url").rstrip("/")
    if api == "mail":
        health_endpoint += "/api/v2/messages"
    else:
        health_endpoint += "/health"

    # Only in case of local testing make sure the internal service is healthy
    if not config.black_box_mode and is_internal:
        health_endpoint = "http://" + health_endpoint.replace(
            config.external_base_url, ""
        ).lstrip("/")

    try:
        response = fixtures.http.get(health_endpoint)
    except Exception as e:
        print("cannot check", health_endpoint, e)
        raise

    status_code = response.status_code
    expected_status = 404 if config.black_box_mode and is_internal else 200
    if status_code == 200 and response.text.startswith("<!doctype html>"):
        # count response from frontend as "not found"
        status_code = 404
    msg = None
    if status_code != expected_status:
        msg = f"status should be {expected_status}, but is {status_code}"
        if expected_status == 404 and status_code == 503:
            msg += " (maybe the frontend is not running?)"
    elif not is_internal:
        try:
            ret = response.json()
        except JSONDecodeError as e:
            if api == "auth_adapter":
                ok = True
            else:
                msg = f"does not return JSON object: {e}"
        else:
            if not isinstance(ret, dict):
                msg = "does not return JSON object"
            if api == "mail":
                ok = "total" in ret
            else:
                ok = ret.get("status") == "OK"
            if not ok:
                msg = f"unexpected response: {ret}"
    assert not msg, f"Health check at endpoint {health_endpoint}: {msg}"
    if api == "ums":
        user_id = check_user_management_apis_are_healthy(fixtures)
        check_claims_repository(fixtures, user_id)


def check_user_management_apis_are_healthy(fixtures: JointFixture):
    """Check health and security of user management APIs more thoroughly."""
    name = "Data Steward"
    sub = fixtures.auth.get_sub(name)
    ums_url = fixtures.config.ums_url
    session = fixtures.auth.fetch_session(name=name, user_id=sub)
    response = fixtures.auth.authenticate(
        session=session,
        state_store=fixtures.state,
        recreate_totp=True,
    )
    status_code = response.status_code
    assert status_code == 204, f"Error {status_code} when authenticating {name}"
    url = f"{ums_url}/users/{session.user_id}"
    headers = fixtures.auth.headers(session)
    response = fixtures.http.get(url, headers=headers)
    status_code = response.status_code
    assert status_code == 200, f"Error {status_code} when requesting info for {name}"
    ret = response.json()
    assert isinstance(ret, dict), f"Bad return value when requesting info for {name}"
    user_id = ret.get("id")
    assert user_id, f"No user ID when requesting info for {name}"
    assert user_id == session.user_id, f"Unexpected user ID for {name}"
    return user_id


def check_claims_repository(fixtures: JointFixture, user_id: str):
    """Check that the core claims API is not accessible."""
    url = f"{fixtures.config.ums_url}/users/{user_id}/claims"
    response = fixtures.http.get(url)
    status_code = response.status_code
    assert status_code == 404, (
        "The claims API should not be accessible,"
        f" but responds with status code {status_code}"
    )


@when("all service APIs are checked", target_fixture="apis")
def list_of_all_service_apis(config: Config) -> list[str]:
    return config.external_apis + config.internal_apis


@then("they report as being healthy")
def check_service_health(apis: list[str], fixtures: JointFixture):
    """Check health of all service APIs depending on the test mode."""
    for api in apis:
        check_api_is_healthy(api, fixtures)


@then("we have a valid Data Steward account for testing")
def check_data_steward_account(fixtures: JointFixture):
    """Check that we have a valid Data Steward account for testing."""
    if not fixtures.config.black_box_mode:
        data_steward_claim = fixtures.mongo.wait_for_documents(
            fixtures.config.ums_db_name,
            fixtures.config.ums_claims_collection,
            {
                "visa_type": "https://www.ghga.de/GA4GH/VisaTypes/Role/v1.0",
                "visa_value": "data_steward@ghga.de",
            },
        )
        assert data_steward_claim, (
            f"Data steward claim not found in {fixtures.config.ums_db_name}."
        )
        assert len(data_steward_claim) == 1, (
            f"Multiple data steward claims found in {fixtures.config.ums_db_name}."
            "Expected: 1."
        )
