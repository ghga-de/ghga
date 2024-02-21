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

"""Step definitions for Data Portal UI"""

from .conftest import (
    JointFixture,
    Response,
    scenarios,
    then,
    when,
)

scenarios("../features/50_data_portal.feature")


@when("the data portal ui is accessed", target_fixture="response")
def check_data_portal_is_healthy(fixtures: JointFixture):
    data_portal_ui_url = fixtures.config.data_portal_ui_url
    response = fixtures.http.get(data_portal_ui_url)
    return response


@when("the service logo is loaded", target_fixture="response")
def load_content(fixtures: JointFixture):
    data_portal_ui_url = fixtures.config.data_portal_ui_url
    service_logo_url = data_portal_ui_url.lstrip("/") + "/service-logo.png"
    response = fixtures.http.get(service_logo_url)
    return response


@then("the content is verified")
def verify_content(response: Response):
    headers = response.headers
    assert headers["content-type"] == "image/png"
    assert headers["content-disposition"] == 'inline; filename="service-logo.png"'
