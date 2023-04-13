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

"""Test dummy."""
import pytest
from hexkit.providers.akafka.testutils import kafka_fixture  # noqa: F401

from tests.fixtures.joint import JointFixture, joint_fixture  # noqa: F401


@pytest.mark.asyncio
async def test_basic_consume(joint_fixture: JointFixture):  # noqa: F811
    """Verify that the consumer runs the dummy _send_email() and raises the error."""
    await joint_fixture.kafka.publish_event(
        payload={"key": "value"},
        type_=joint_fixture.config.notification_event_type,
        topic=joint_fixture.config.notification_event_topic,
    )

    event_subscriber = await joint_fixture.container.kafka_event_subscriber()
    with pytest.raises(NotImplementedError):
        await event_subscriber.run(forever=False)
