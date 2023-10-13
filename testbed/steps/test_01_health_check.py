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

from urllib.parse import urljoin

import httpx
from fixtures.http import TIMEOUT
from pytest_bdd import given, scenarios

from .conftest import Config

scenarios("../features/01_health_check.feature")


def check_api_health(api, config, expected_status_code):
    """Check service API returns expected status code"""
    service_url = getattr(config, f"{api}_url")
    endpoint = urljoin(service_url, "health")
    if api == "mail":
        endpoint = service_url  # Mail service has no /health endpoint
    response = httpx.get(endpoint, timeout=TIMEOUT)
    assert (
        response.status_code == expected_status_code
    ), f"Service did not return expected status code {expected_status_code}: {service_url}"


@given("all the service APIs respond as expected")
def check_service_health(config: Config):
    """Check 'health' endpoint of all service APIs"""
    if config.use_api_gateway:
        # black-box testing: external APIs are accessible internal APIs are not
        for ext_api in config.external_apis:
            check_api_health(ext_api, config, 200)
        for int_api in config.internal_apis:
            check_api_health(int_api, config, 404)
    else:
        # white-box testing: all of the APIs are accessible
        all_apis = config.external_apis + config.internal_apis
        for api in all_apis:
            check_api_health(api, config, 200)
