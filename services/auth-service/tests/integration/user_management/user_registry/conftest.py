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

"""Test configuration for the user management"""

from pytest import fixture

from ....fixtures import auth_keys
from ....fixtures.utils import get_headers_for


@fixture(autouse=True, scope="package")
def config_for_user_registry() -> None:
    """Set the environment for the user registry"""
    auth_keys.reload_auth_key_config(auth_adapter=False)


@fixture(autouse=True, scope="package")
def new_user_headers() -> dict[str, str]:
    """Get headers with authorization for a new (unregistered) user."""
    return get_headers_for(
        id="max@ls.org", name="Max Headroom", email="max@example.org"
    )


@fixture(autouse=True, scope="package")
def user_headers() -> dict[str, str]:
    """Get headers with authorization for an existing (registered) user."""
    return get_headers_for(
        id="max-internal", name="Max Headroom", email="max@example.org"
    )


@fixture(autouse=True, scope="package")
def steward_headers() -> dict[str, str]:
    """Get headers with authorization for a user with data steward role."""
    return get_headers_for(
        id="steve-internal",
        name="Steve Steward",
        email="steve@archive.org",
        role="data_steward",
    )
