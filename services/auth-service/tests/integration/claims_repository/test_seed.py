# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

import logging
from datetime import datetime
from typing import Any

import pytest
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb import MongoDbDaoFactory
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.providers.mongokafka import MongoKafkaDaoPublisherFactory

from auth_service.claims_repository.core.seed import (
    seed_data_steward_claims,
)
from auth_service.claims_repository.models.config import (
    IvaType,
    UserWithIVA,
)
from auth_service.claims_repository.translators.dao import (
    ClaimDaoFactory,
)
from auth_service.config import Config
from auth_service.user_registry.translators.dao import (
    UserDaoPublisherFactory,
)


async def fut(config: Config):
    """Run seed_data_steward_claims (the function under test here)."""
    # prepare the infrastructure
    dao_factory = MongoDbDaoFactory(config=config)
    async with (
        MongoKafkaDaoPublisherFactory.construct(config=config) as dao_publisher_factory,
    ):
        # create DAOs
        user_dao_publisher_factory = UserDaoPublisherFactory(
            config=config, dao_publisher_factory=dao_publisher_factory
        )
        user_dao = await user_dao_publisher_factory.get_user_dao()
        iva_dao = await user_dao_publisher_factory.get_iva_dao()
        claim_dao_factory = ClaimDaoFactory(config=config, dao_factory=dao_factory)
        claim_dao = await claim_dao_factory.get_claim_dao()
        # run the actual function
        await seed_data_steward_claims(
            config=config, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
        )


@pytest.mark.asyncio()
async def test_add_data_steward(
    mongodb: MongoDbFixture, kafka: KafkaFixture, caplog: pytest.LogCaptureFixture
):
    """Test that existing and non-existing data stewards can be added."""
    config = Config(
        mongo_dsn=mongodb.config.mongo_dsn,
        db_name=mongodb.config.db_name,
        kafka_servers=kafka.config.kafka_servers,
        service_name=kafka.config.service_name,
        service_instance_id=kafka.config.service_instance_id,
        provide_apis=["claims"],
        add_as_data_stewards=[
            UserWithIVA(
                ext_id="id-of-john-doe@ls.org",
                name="John Doe",
                email="john@home.org",
                iva_type=IvaType.IN_PERSON,
                iva_value="Some address",
            )
        ],
    )

    # add non-existing data steward

    caplog.set_level(logging.INFO)
    caplog.clear()

    await fut(config)

    records = [record for record in caplog.records if record.module == "seed"]

    log_messages = [record.message for record in records]
    num_warnings = sum(record.levelno >= logging.WARNING for record in records)
    assert num_warnings == 2
    assert log_messages == [
        "Removed 0 existing data steward claim(s).",
        "Added missing data steward with external ID 'id-of-john-doe@ls.org'.",
        "Added missing IVA for data steward with external ID 'id-of-john-doe@ls.org'.",
        "Added data steward role for 'id-of-john-doe@ls.org' to the claims repository.",
    ]

    db = mongodb.client.get_database(config.db_name)
    users_collection = db.get_collection(config.users_collection)
    users = list(users_collection.find())

    assert len(users) == 1
    user: dict[str, Any] = users[0]
    assert user["name"] == "John Doe"
    assert user["email"] == "john@home.org"
    assert user["title"] is None
    assert user["ext_id"] == "id-of-john-doe@ls.org"
    assert user["status"] == "active"

    ivas_collection = db.get_collection(config.ivas_collection)
    ivas = list(ivas_collection.find())

    assert len(ivas) == 1
    iva: dict[str, Any] = ivas[0]
    assert iva["user_id"] == user["_id"]
    assert iva["type"] == "InPerson"
    assert iva["value"] == "Some address"
    assert iva["state"] == "Unverified"
    assert iva["verification_attempts"] == 0
    assert iva["verification_code_hash"] is None
    creation_date = iva["created"]
    time_diff = now_as_utc() - datetime.fromisoformat(creation_date)
    assert -1 < time_diff.total_seconds() < 3
    assert iva["changed"] == iva["created"]

    claims_collection = db.get_collection(config.claims_collection)
    claims = list(claims_collection.find())

    assert len(claims) == 1
    claim: dict[str, Any] = claims[0]
    assert claim["user_id"] == user["_id"]
    assert claim["visa_type"] == "https://www.ghga.de/GA4GH/VisaTypes/Role/v1.0"
    assert claim["visa_value"] == "data_steward@ghga.de"
    assert claim["asserted_by"] == "system"
    assert claim["source"] == "https://ghga.de"
    assert claim["sub_source"] is None
    assert claim["conditions"] is None
    creation_date = claim["creation_date"]
    time_diff = now_as_utc() - datetime.fromisoformat(creation_date)
    assert -1 < time_diff.total_seconds() < 3
    assert claim["assertion_date"] == creation_date
    assert claim["valid_from"] == creation_date
    assert (
        datetime.fromisoformat(claim["valid_until"])
        - datetime.fromisoformat(claim["valid_from"])
    ).days == 365
    assert claim["revocation_date"] is None
    assert claim["iva_id"] == iva["_id"]

    # add existing data steward

    caplog.clear()

    await fut(config)

    records = [record for record in caplog.records if record.module == "seed"]

    log_messages = [record.message for record in records]
    num_warnings = sum(record.levelno >= logging.WARNING for record in records)
    assert num_warnings == 0
    assert log_messages == [
        "Removed 1 existing data steward claim(s).",
        "Added data steward role for 'id-of-john-doe@ls.org' to the claims repository.",
    ]

    assert list(users_collection.find()) == users
    assert list(ivas_collection.find()) == ivas

    new_claims = list(claims_collection.find())
    assert new_claims != claims

    new_claim = new_claims[0]
    assert new_claim.pop("_id") != claim.pop("_id")
    for date_field in [
        "creation_date",
        "assertion_date",
        "valid_from",
        "valid_until",
    ]:
        time_diff = datetime.fromisoformat(
            new_claim.pop(date_field)
        ) - datetime.fromisoformat(claim.pop(date_field))
        assert -1 < time_diff.total_seconds() < 3
    assert new_claim == claim

    # add data steward with different name

    users_collection.update_one({"_id": user["_id"]}, {"$set": {"name": "Jane Roe"}})

    with pytest.raises(
        ValueError,
        match="Configured data steward with external ID id-of-john-doe@ls.org"
        " has the name 'Jane Roe', expected was 'John Doe'",
    ):
        await fut(config)

    # add data steward with different email address

    users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"name": "John Doe", "email": "jane@home.org"}},
    )

    with pytest.raises(
        ValueError,
        match="Configured data steward with external ID id-of-john-doe@ls.org"
        " has the email address <jane@home.org>, expected was <john@home.org>",
    ):
        await fut(config)
