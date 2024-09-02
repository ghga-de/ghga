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

"""Fixture for testing code that uses the Kafka-based provider."""

from typing import Union

from pytest import fixture

from fixtures.config import Config
from fixtures.http_client import HttpClient
from fixtures.state_manager import StateManager

__all__ = ["kafka_fixture", "KafkaFixture"]


class KafkaFixture(StateManager):
    """Fixture for managing Kafka resources."""

    def __init__(self, config: Config, http: HttpClient):
        self.config = config
        self.http = http

    config: Config

    def clear_topics(
        self, topics: str | list[str] | None = None, exclude_internal: bool = True
    ) -> None:
        """Delete all messages in the given topics.

        If no topics are specified, all topics will be cleared,
        except internal topics unless otherwise specified.
        """
        url = f"{self.config.sms_url}/events/"
        params: dict[str, bool | list[str]] = {}

        if isinstance(topics, str):
            topics = [topics]

        if topics:
            params["topics"] = topics

        if not exclude_internal:
            params["exclude_internal"] = exclude_internal

        response = self.http.delete(url, headers=self.auth_headers, params=params)
        assert response.status_code == 204, f"Failed to clear topics: {response.text}"


@fixture(name="kafka", scope="session")
def kafka_fixture(config: Config, http: HttpClient) -> KafkaFixture:
    """Pytest fixture for tests depending on the Kafka-based provider."""
    return KafkaFixture(config=config, http=http)
