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

"""Test deletion of claims."""

import logging
from datetime import timedelta
from uuid import uuid4

import pytest
from hexkit.protocols.dao import NoHitsFoundError
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb import MongoDbDaoFactory
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.utils import now_utc_ms_prec

from auth_service.claims_repository.models.claims import (
    AuthorityLevel,
    Claim,
    VisaType,
)
from auth_service.claims_repository.translators.dao import (
    ClaimDaoFactory,
)
from auth_service.config import Config
from auth_service.prepare import prepare_event_subscriber
from tests.fixtures.constants import SOME_USER_ID


@pytest.mark.asyncio()
async def test_deletion_handler(
    kafka: KafkaFixture,
    mongodb: MongoDbFixture,
    caplog: pytest.LogCaptureFixture,
):
    """Test the dataset deletion handler"""
    config = Config(
        mongo_dsn=mongodb.config.mongo_dsn,
        db_name=mongodb.config.db_name,
        kafka_servers=kafka.config.kafka_servers,
        service_name=kafka.config.service_name,
        service_instance_id=kafka.config.service_instance_id,
        provide_apis=[],
        add_as_data_stewards=[],
        migration_wait_sec=2,
        db_version_collection="authDbVersions",
    )

    async with MongoDbDaoFactory.construct(config=config) as dao_factory:
        claim_dao_factory = ClaimDaoFactory(config=config, dao_factory=dao_factory)
        claim_dao = await claim_dao_factory.get_claim_dao()

        now = now_utc_ms_prec()
        claim = Claim(
            id=uuid4(),
            visa_type=VisaType.CONTROLLED_ACCESS_GRANTS,
            visa_value="https://ghga.de/datasets/DS0815",
            assertion_date=now,
            valid_from=now,
            valid_until=now + timedelta(1),
            source="https://ghga.de",  # type: ignore[arg-type]
            sub_source=None,
            asserted_by=AuthorityLevel.DAC,
            user_id=SOME_USER_ID,
            conditions=None,
            revocation_date=None,
            creation_date=now,
        )

        await claim_dao.insert(claim)
        assert await claim_dao.find_one(mapping={"user_id": SOME_USER_ID})

        event_type = config.dataset_deletion_type
        event_topic = config.dataset_change_topic
        payload = {"accession": "DS0815"}

        async with prepare_event_subscriber(config=config) as event_subscriber:
            caplog.set_level(logging.INFO)

            await kafka.publish_event(
                payload=payload, type_=event_type, topic=event_topic
            )
            caplog.clear()
            await event_subscriber.run(forever=False)
            records = caplog.records
            messages = [
                record.message
                for record in records
                if record.module in ("eventsub", "deletion")
            ]

            assert len(messages) == 2, messages
            # TODO: Fix bug in hexkit - wrong logging message!
            # assert messages[0].startswith("Consuming event of type 'dataset_deleted'")
            assert messages[0].startswith("Ignored event")
            assert messages[1] == "Deleted 1 claims for dataset DS0815"
            with pytest.raises(NoHitsFoundError):
                assert not await claim_dao.find_one(mapping={"user_id": SOME_USER_ID})

            await kafka.publish_event(
                payload=payload, type_=event_type, topic=event_topic
            )
            caplog.clear()
            await event_subscriber.run(forever=False)
            messages = [
                record.message
                for record in records
                if record.module in ("eventsub", "deletion")
            ]

            assert len(messages) == 2, messages
            # TODO: Fix bug in hexkit - wrong logging message!
            # assert messages[0].startswith("Consuming event of type 'dataset_deleted'")
            assert messages[0].startswith("Ignored event")
            assert messages[1] == "Deleted 0 claims for dataset DS0815"
