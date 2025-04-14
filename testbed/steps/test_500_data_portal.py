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

"""Step definitions for Data Portal"""

import hashlib

from .conftest import (
    JointFixture,
    Response,
    scenarios,
    then,
    when,
)

scenarios("../features/500_data_portal.feature")


@when("the data portal is accessed", target_fixture="response")
def check_data_portal_is_healthy(fixtures: JointFixture):
    data_portal_url = fixtures.config.data_portal_url
    response = fixtures.http.get(data_portal_url)
    return response


@when("the favicon is loaded", target_fixture="response")
def load_content(fixtures: JointFixture):
    data_portal_url = fixtures.config.data_portal_url
    favicon_url = data_portal_url.lstrip("/") + "/favicon.png"
    response = fixtures.http.get(favicon_url)
    return response


@then("the favicon is verified")
def verify_favicon(response: Response):
    expected_content_hash = (
        "222882c2bb5d6bb58f8fa2171641a24e36c0e2c8265217065316c28f0ebf054c"
    )
    headers = response.headers
    assert headers["content-type"] == "image/png"
    assert headers["content-length"] == "16760"
    favicon_hash = hashlib.sha256(response.content).hexdigest()
    assert favicon_hash == expected_content_hash, (
        "Favicon hash does not match the known hash"
    )
