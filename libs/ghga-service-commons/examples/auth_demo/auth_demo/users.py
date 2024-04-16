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

"""Create access tokens for testing."""

from typing import NamedTuple

from auth_demo.auth.config import AUTH_KEY_PAIR
from ghga_service_commons.utils.jwt_helpers import sign_and_serialize_token


class UserInfo(NamedTuple):
    """Basic user info."""

    name: str
    is_vip: bool


EXAMPLE_USERS: list[UserInfo] = [
    UserInfo("Ada Lovelace", False),
    UserInfo("Grace Hopper", True),
    UserInfo("Charles Babbage", False),
    UserInfo("Alan Turing", True),
]


def create_example_users() -> list[dict]:
    """Create a couple of example users for the application."""
    users = [user._asdict() for user in EXAMPLE_USERS]
    for user in users:
        user["token"] = sign_and_serialize_token(user, AUTH_KEY_PAIR)
    return users
