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

"""Storage fixture for state management between test cases."""

import re
from abc import ABC, abstractmethod
from typing import Any

from pytest import fixture

from fixtures.config import Config
from fixtures.mongo import MongoFixture


class StateStorage(ABC):
    """Base class representing a storage for the state of the test bed

    Provides mechanisms for storing and managing the state"""

    @abstractmethod
    def get_state(self, state_name: str) -> Any:
        """Retrieve the state for a given key."""
        ...

    @abstractmethod
    def set_state(self, state_name: str, value: Any) -> None:
        """Set the state for a given key."""
        ...

    @abstractmethod
    def unset_state(self, state_regex: str) -> None:
        """Remove the state matching a regex string."""
        ...

    @abstractmethod
    def reset_state(self) -> None:
        """Reset the state storage to empty slate."""
        ...


class MemoryStateStorage(StateStorage):
    """In-memory state storage implementing StateStorage"""

    def __init__(self):
        self.memory_storage = {}

    def get_state(self, state_name: str) -> Any:
        return self.memory_storage.get(state_name)

    def set_state(self, state_name: str, value: Any):
        self.memory_storage[state_name] = value

    def unset_state(self, state_regex: str):
        regex = re.compile(state_regex)
        for state_name, _ in self.memory_storage.items():
            if regex.match(state_name):
                del self.memory_storage[state_name]

    def reset_state(self):
        self.memory_storage.clear()


class MongoStateStorage(StateStorage):
    """Mongo state storage implementing StateStorage"""

    DB_NAME = "tb"
    COLLECTION_NAME = "state"

    def __init__(self, mongo: MongoFixture):
        self.mongo = mongo

    def get_state(self, state_name: str) -> Any:
        state = self.mongo.find_document(
            self.DB_NAME, self.COLLECTION_NAME, {"_id": state_name}
        )
        return (state or {}).get("value")

    def set_state(self, state_name: str, value: Any):
        self.mongo.replace_document(
            self.DB_NAME, self.COLLECTION_NAME, {"_id": state_name, "value": value}
        )

    def unset_state(self, state_regex: str):
        self.mongo.remove_document(
            self.DB_NAME, self.COLLECTION_NAME, {"_id": {"$regex": state_regex}}
        )

    def reset_state(self):
        self.mongo.empty_databases(self.DB_NAME)


@fixture(name="state", scope="session")
def state_fixture(config: Config, mongo: MongoFixture) -> StateStorage:
    """Fixture that provides a state storage."""
    storage = (
        MongoStateStorage(mongo=mongo)
        if config.keep_state_in_db
        else MemoryStateStorage()
    )

    return storage
