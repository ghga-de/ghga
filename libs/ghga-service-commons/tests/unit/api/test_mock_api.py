# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Testing the setup checks of the MockedApi."""

import pytest

from ghga_service_commons.api.mock_api import MockedApi, MockSetupError, endpoint


def test_endpoints_serving_the_same_route_are_rejected():
    """Test that two endpoints for one method and path fail when the mock is built.

    The second spells the route differently, which `Endpoint` normalizes to the same.
    """

    class MockedDuplicateApi(MockedApi):
        base_url = "http://duplicate.test"
        on_first = endpoint("GET", "/things")
        on_second = endpoint("get", "things")

    with pytest.raises(
        MockSetupError, match=r"GET /things as both 'on_first' and 'on_second'"
    ):
        MockedDuplicateApi()


def test_one_endpoint_bound_under_two_names_is_rejected():
    """Test that aliasing an endpoint inside a class body counts as a duplicate."""

    class MockedAliasApi(MockedApi):
        base_url = "http://alias.test"
        on_things = endpoint("GET", "/things")
        list_things = on_things

    with pytest.raises(MockSetupError, match=r"'on_things' and 'list_things'"):
        MockedAliasApi()


def test_other_methods_and_overrides_are_not_duplicates():
    """Test that other methods on one path, and a subclass override, are allowed."""

    class MockedBaseApi(MockedApi):
        base_url = "http://distinct.test"
        on_get_thing = endpoint("GET", "/things/{thing_id}")
        on_delete_thing = endpoint("DELETE", "/things/{thing_id}")

    class MockedSubApi(MockedBaseApi):
        on_get_thing = endpoint("GET", "/things/{thing_id}")

    MockedBaseApi()
    MockedSubApi()
