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

"""Test deletion of claims."""

import logging
from datetime import timedelta

from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.protocols.dao import NoHitsFoundError
from hexkit.providers.akafka.testutils import KafkaFixture, kafka_fixture  # noqa: F401
from pydantic import SecretStr
from pytest import LogCaptureFixture, mark, raises

from auth_service.__main__ import get_claim_dao, prepare_event_subscriber
from auth_service.config import CONFIG
from auth_service.user_management.claims_repository.models.claims import (
    AuthorityLevel,
    Claim,
    VisaType,
)

from .fixtures import MongoDbContainer, fixture_mongodb  # noqa: F401


@mark.asyncio()
async def test_deletion_handler(
    kafka_fixture: KafkaFixture,  # noqa: F811
    mongodb: MongoDbContainer,
    caplog: LogCaptureFixture,
):
    """Test the dataset deletion handler"""
    config = CONFIG.model_copy(
        update={
            "db_connection_str": SecretStr(mongodb.get_connection_url()),
            "kafka_servers": kafka_fixture.kafka_servers,
        }
    )

    now = now_as_utc()
    claim = Claim(
        id="some-claim-id",
        visa_type=VisaType.CONTROLLED_ACCESS_GRANTS,
        visa_value="https://ghga.de/datasets/some-dataset-id",
        assertion_date=now,
        valid_from=now,
        valid_until=now + timedelta(1),
        source="https://ghga.de",  # type: ignore[arg-type]
        sub_source=None,
        asserted_by=AuthorityLevel.DAC,
        user_id="some-user-id",
        conditions=None,
        revocation_date=None,
        creation_date=now,
    )
    claim_dao = await get_claim_dao(config=config)
    await claim_dao.insert(claim)
    assert await claim_dao.find_one(mapping={"user_id": "some-user-id"})

    event_type = config.dataset_deletion_event_type
    event_topic = config.dataset_deletion_event_topic
    payload = {"accession": "some-dataset-id"}

    async with prepare_event_subscriber(config=config) as event_subscriber:
        caplog.set_level(logging.INFO)
        caplog.clear()
        await kafka_fixture.publish_event(
            payload=payload, type_=event_type, topic=event_topic
        )
        await event_subscriber.run(forever=False)
        records = caplog.records
        assert len(records) == 4, records
        messages = [record.message for record in records]
        messages = [message for message in messages if "correlation" not in message]
        assert len(messages) == 2, messages
        assert messages[0].startswith('Consuming event of type "dataset_deleted"')
        assert messages[1] == "Deleted 1 claims for dataset some-dataset-id"
        with raises(NoHitsFoundError):
            assert not await claim_dao.find_one(mapping={"user_id": "some-user-id"})

        caplog.clear()
        await kafka_fixture.publish_event(
            payload=payload, type_=event_type, topic=event_topic
        )
        await event_subscriber.run(forever=False)
        assert len(records) == 4, records
        messages = [record.message for record in records]
        messages = [message for message in messages if "correlation" not in message]
        assert len(messages) == 2, messages
        assert messages[0].startswith('Consuming event of type "dataset_deleted"')
        assert messages[1] == "Deleted 0 claims for dataset some-dataset-id"
