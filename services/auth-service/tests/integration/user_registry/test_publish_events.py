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

"""Test the `publish-events` entry point."""

import pytest

from auth_service import main
from auth_service.config import Config
from auth_service.prepare import prepare_user_dao_publisher_factory
from auth_service.user_registry.models.users import (
    StatusChange,
    User,
    UserStatus,
)
from ghga_service_commons.utils.utc_dates import utc_datetime
from hexkit.correlation import set_new_correlation_id
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture

pytestmark = pytest.mark.asyncio()


def make_user(name: str) -> User:
    """Make an active user with the given name."""
    return User(
        ext_id=f"{name.lower()}@ls.org",
        status=UserStatus.ACTIVE,
        name=name,
        email=f"{name.lower()}@example.org",
        registration_date=utc_datetime(2022, 9, 1, 12, 0),
        status_change=StatusChange(previous=None, by=None, context="test"),
    )


async def test_publish_events(
    mongodb: MongoDbFixture, kafka: KafkaFixture, monkeypatch: pytest.MonkeyPatch
):
    """Publish only the pending user, and with `all` every user."""
    config = Config(
        mongo_dsn=mongodb.config.mongo_dsn,
        db_name=mongodb.config.db_name,
        kafka_servers=kafka.config.kafka_servers,
        service_name=kafka.config.service_name,
        service_instance_id=kafka.config.service_instance_id,
        migration_wait_sec=2,
        db_version_collection="authDbVersions",
    )
    monkeypatch.setattr(main, "Config", lambda: config)
    monkeypatch.setattr(main, "configure_logging", lambda config: None)
    published, pending = make_user("Max"), make_user("Moritz")

    async with (
        set_new_correlation_id(),
        prepare_user_dao_publisher_factory(config) as factory,
    ):
        user_dao = await factory.get_user_dao()
        await user_dao.insert(published)
        await user_dao.insert(pending)
    # a failed publish leaves the change marked as not yet published
    mongodb.client[config.db_name][config.users_collection].update_one(
        {"_id": pending.id}, {"$set": {"__metadata__.published": False}}
    )

    async with kafka.record_events(in_topic=config.user_topic) as recorder:
        await main.publish_events()
    assert [event.key for event in recorder.recorded_events] == [str(pending.id)]

    async with kafka.record_events(in_topic=config.user_topic) as recorder:
        await main.publish_events(all=True)
    assert {event.key for event in recorder.recorded_events} == {
        str(published.id),
        str(pending.id),
    }
