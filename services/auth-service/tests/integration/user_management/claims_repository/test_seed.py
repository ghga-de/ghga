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

"""Test seeding the database with data stewards."""

import asyncio
import logging

from pydantic import SecretStr
from testcontainers.mongodb import MongoDbContainer

from auth_service.config import Config
from auth_service.user_management.claims_repository.core.seed import (
    seed_data_steward_claims,
)


def test_add_non_existing_data_steward(caplog):
    """Test that non-existing data stewards can be added in the configuration."""
    with MongoDbContainer() as mongodb:
        config = Config(
            db_connection_str=SecretStr(mongodb.get_connection_url()),
            db_name="test-claims-repository",
            include_apis=["claims"],
            add_as_data_stewards=[
                {
                    "name": "John Doe",
                    "email": "john@home.org",
                    "ext_id": "id-of-john-doe@ls.org",
                },
                "id-of-jane-roe@ls.org",
            ],
        )  # type: ignore

        caplog.set_level(logging.INFO)
        caplog.clear()
        asyncio.run(seed_data_steward_claims(config))
        records = [record for record in caplog.records if record.module == "seed"]
        log_messages = [record.message for record in records]
        num_warnings = sum(record.levelno >= logging.WARNING for record in records)

        client = mongodb.get_connection_client()
        db = client.get_database(config.db_name)
        users_collection = db.get_collection(config.users_collection)
        users = list(users_collection.find())

    assert num_warnings == 2
    assert log_messages == [
        "Removed 0 existing data steward claim(s).",
        "Added missing data steward with external ID 'id-of-john-doe@ls.org'.",
        "Added data steward role for 'id-of-john-doe@ls.org' to the claims repository.",
        "Could not add new user with external ID 'id-of-jane-roe@ls.org':"
        " User data (name and email) is missing.",
    ]

    assert len(users) == 1
    user = users[0]
    assert user["name"] == "John Doe"
    assert user["email"] == "john@home.org"
    assert user["title"] is None
    assert user["ext_id"] == "id-of-john-doe@ls.org"
    assert user["status"] == "active"
