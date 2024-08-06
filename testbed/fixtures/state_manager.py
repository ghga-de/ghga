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

"""Fixture for managing resources."""

import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from pytest import fixture

from fixtures.config import Config
from fixtures.http_client import HttpClient


class StateManager:
    """Fixture for resource management."""

    def __init__(self, config: Config, http: HttpClient):
        self.config = config
        self.http = http

    @property
    def auth_headers(self) -> dict[str, str]:
        """Returns the authorization headers for the state management API."""
        return {"Authorization": f"Bearer {self.config.state_management_token}"}

    @staticmethod
    def stringify_query_params(query: Mapping[str, Any]):
        """Encode URL parameters to pass the state management API safely."""
        return {
            k: quote(json.dumps(v)) if isinstance(v, dict) else v
            for k, v in query.items()
        }


@fixture(name="state_manager", scope="session")
def state_manager_fixture(config: Config, http: HttpClient) -> StateManager:
    """Pytest fixture for resource management."""
    return StateManager(config=config, http=http)
