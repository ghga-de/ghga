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

"""Step definition for service health check using health endpoint"""

from pytest_bdd import scenarios, then, when

from .conftest import Config, JointFixture

scenarios("../features/01_health_check.feature")


def check_api_is_healthy(api: str, fixtures: JointFixture):
    """Check that service API is healthy or not reachable if internal."""
    config = fixtures.config
    is_internal = config.use_api_gateway and api in config.internal_apis
    health_endpoint = getattr(config, f"{api}_url").rstrip("/")
    if api == "mail":
        health_endpoint += "/api/v2/messages"
    else:
        health_endpoint += "/health"
    response = fixtures.http.get(health_endpoint)
    status_code = response.status_code
    expected_status = 404 if is_internal else 200
    if status_code == 200 and response.text.startswith("<!doctype html>"):
        # count response from frontend as "not found"
        status_code = 404
    msg = None
    if status_code != expected_status:
        msg = f"status should be {expected_status}, but is {status_code}"
    elif not is_internal:
        ret = response.json()
        if not isinstance(ret, dict):
            msg = "does not return JSON object"
        if api == "mail":
            ok = "total" in ret
        elif api == "auth_adapter":
            ok = not ret
        else:
            ok = ret.get("status") == "OK"
        if not ok:
            msg = f"unexpected response: {ret}"
    assert not msg, f"Health check at endpoint {health_endpoint}: {msg}"
    if api == "ums":
        check_user_management_apis_are_healthy(fixtures)


def check_user_management_apis_are_healthy(fixtures: JointFixture):
    """Check health and security of user management APIs more thoroughly."""
    name = "Data Steward"
    sub = fixtures.auth.get_sub(name)
    ums_url = fixtures.config.ums_url
    endpoint = f"{ums_url}/users/{sub}"
    headers = fixtures.auth.generate_headers(name)
    response = fixtures.http.get(endpoint, headers=headers)
    status_code = response.status_code
    assert status_code == 200, f"Error {status_code} when requesting info for {name}"
    ret = response.json()
    assert isinstance(ret, dict), f"Bad return value when requesting info for {name}"
    user_id = ret.get("id")
    assert user_id, f"No user ID when requesting info for {name}"
    endpoint = f"{ums_url}/users/{user_id}/claims"
    response = fixtures.http.get(endpoint)
    status_code = response.status_code
    if fixtures.config.use_api_gateway:
        assert status_code == 404, (
            "The claims repository should bot be reachable from outside,"
            f" but responds with status code {status_code}"
        )
    else:
        assert (
            status_code == 200
        ), f"Error {status_code} when requesting claims for {name}"
        ret = response.json()
        if not (
            isinstance(ret, list)
            and len(ret) == 1
            and ret[0]["visa_type"] == "https://www.ghga.de/GA4GH/VisaTypes/Role/v1.0"
            and ret[0]["visa_value"] == "data_steward@ghga.de"
        ):
            assert False, f"{name} should have exactly one data steward claim"


@when("all service APIs are checked", target_fixture="apis")
def list_of_all_service_apis(config: Config) -> list[str]:
    return config.external_apis + config.internal_apis


@then("they report as being healthy")
def check_service_health(apis: list[str], fixtures: JointFixture):
    """Check health of all service APIs depending on the test mode."""
    for api in apis:
        check_api_is_healthy(api, fixtures)
