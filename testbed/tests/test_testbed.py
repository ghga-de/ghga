# Copyright 2022 Universität Tübingen, DKFZ and EMBL
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

import time
from datetime import datetime

import pytest  # type: ignore
from ghga_event_schemas import pydantic_ as event_schemas  # type: ignore
from hexkit.providers.akafka import KafkaEventPublisher  # type: ignore
from hexkit.providers.akafka.testutils import EventRecorder  # type: ignore

from tests.fixtures.config import CONFIG
from tests.fixtures.local_fixtures import populated_s3_fixture  # noqa: F401
from tests.fixtures.local_fixtures import PopulatedS3Fixture


@pytest.mark.asyncio
async def test_outbound_payload(
    populated_s3_fixture: PopulatedS3Fixture,  # noqa: F811
):
    """Test response event receival"""

    event = event_schemas.FileUploadReceived(
        file_id=CONFIG.object_id,
        submitter_public_key=CONFIG.submitter_pubkey,
        upload_date=datetime.utcnow().isoformat(),
        decrypted_size=populated_s3_fixture.file_size,
        expected_decrypted_sha256=populated_s3_fixture.checksum,
    )

    async with EventRecorder(
        kafka_servers=CONFIG.kafka_servers, topic="file_interrogation"
    ) as event_recorder:
        async with KafkaEventPublisher.construct(config=CONFIG) as publisher:
            type_ = "file_upload_received"
            key = CONFIG.object_id
            topic = "file_uploads"
            await publisher.publish(
                payload=event.dict(),
                type_=type_,
                key=key,
                topic=topic,
            )
        time.sleep(10)

    assert len(event_recorder.recorded_events) == 1

    payload = event_recorder.recorded_events[0].payload
    assert "upload_date" in payload.keys()
    assert payload["file_id"] == CONFIG.object_id
    assert payload["reason"] == "The crypt4GH envelope is either malformed or missing."
