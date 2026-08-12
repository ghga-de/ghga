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

"""Tests that spans are recorded. No REST API here, so MongoDB, S3 and Kafka."""

import inspect
from collections import Counter
from uuid import uuid4

import pytest

from ghga_event_schemas.pydantic_ import NonStagedFileRequested
from hexkit.opentelemetry.testutils import (  # noqa: F401
    otel_fixture,
    otel_provider_fixture,
)
from hexkit.providers.s3.testutils import (
    FileObject,
    tmp_file,  # noqa: F401
)
from ifrs import main
from ifrs.inject import get_persistent_publisher
from tests_ifrs.fixtures.example_data import EXAMPLE_ARCHIVABLE_FILE
from tests_ifrs.fixtures.joint import JointFixture
from tests_ifrs.fixtures.utils import DOWNLOAD_BUCKET, INTERROGATION_BUCKET

pytestmark = pytest.mark.asyncio()


def assert_recorded_spans(otel, expected: list[str]) -> None:
    """Assert the recorded spans match `expected` exactly, counts included.

    MongoDB connection housekeeping (`admin.*`) is emitted on a pool- and
    timing-dependent basis, so it is filtered out before comparing.
    """
    recorded = Counter(
        name for name in otel.get_span_names() if not name.startswith("admin.")
    )
    expected_counts = Counter(expected)
    assert recorded == expected_counts, (
        f"Unexpected spans: {dict(recorded - expected_counts)}; "
        f"missing spans: {dict(expected_counts - recorded)}"
    )


async def test_file_registration_records_spans(
    otel,  # first, so OpenTelemetry is configured before the fixtures below
    joint_fixture: JointFixture,
    tmp_file: FileObject,  # noqa: F811
):
    """Registration touches all three backends: S3, MongoDB and Kafka."""
    storage_alias = joint_fixture.storage_aliases.node0
    storage = joint_fixture.federated_s3.storages[storage_alias]

    file_object = tmp_file.model_copy(
        update={
            "bucket_id": INTERROGATION_BUCKET,
            "object_id": str(EXAMPLE_ARCHIVABLE_FILE.object_id),
        }
    )
    await storage.populate_file_objects(file_objects=[file_object])
    archivable_file = EXAMPLE_ARCHIVABLE_FILE.model_copy(
        update={
            "storage_alias": storage_alias,
            "encrypted_size": len(tmp_file.content),
        },
        deep=True,
    )

    otel.reset()
    await joint_fixture.file_registry.register_file(file=archivable_file)

    assert_recorded_spans(
        otel,
        [
            # Manual spans wrapping the core and the event publisher
            "FileRegistry.register_file",
            "EventPubTranslator.file_internally_registered",
            # Autoinstrumented MongoDB access (pymongo)
            "test.find",
            "test.insert",
            "test.update",
            "test.update",
            # Autoinstrumented object storage (botocore)
            "S3.HeadObject",
            "S3.HeadObject",
            "S3.HeadObject",
            "S3.HeadObject",
            "S3.HeadBucket",
            "S3.CopyObject",
            # Autoinstrumented Kafka producer (aiokafka)
            "internal-file-registry send",
        ],
    )

    # Without the parent link the backend calls would be detached from the trace.
    register_span = otel.assert_has_span("FileRegistry.register_file")
    assert [
        span
        for span in otel.get_finished_spans()
        if span.name.startswith("S3.")
        and span.context.trace_id == register_span.context.trace_id
    ], "No autoinstrumented S3 spans share the manual span's trace"


async def test_consumed_staging_event_records_spans(
    otel,  # first, so OpenTelemetry is configured before the fixtures below
    joint_fixture: JointFixture,
    tmp_file: FileObject,  # noqa: F811
):
    """Event consumption is a separate entry point from the direct core calls above."""
    storage_alias = joint_fixture.storage_aliases.node0
    storage = joint_fixture.federated_s3.storages[storage_alias]

    file_object = tmp_file.model_copy(
        update={
            "bucket_id": INTERROGATION_BUCKET,
            "object_id": str(EXAMPLE_ARCHIVABLE_FILE.object_id),
        }
    )
    await storage.populate_file_objects(file_objects=[file_object])
    archivable_file = EXAMPLE_ARCHIVABLE_FILE.model_copy(
        update={
            "storage_alias": storage_alias,
            "encrypted_size": len(tmp_file.content),
        },
        deep=True,
    )
    await joint_fixture.file_registry.register_file(file=archivable_file)

    staging_request = NonStagedFileRequested(
        file_id=archivable_file.id,
        storage_alias=storage_alias,
        target_bucket_id=DOWNLOAD_BUCKET,
        target_object_id=uuid4(),
        decrypted_sha256=archivable_file.decrypted_sha256,
    )
    await joint_fixture.kafka.publish_event(
        payload=staging_request.model_dump(mode="json"),
        type_=joint_fixture.config.files_to_stage_type,
        topic=joint_fixture.config.files_to_stage_topic,
        key=str(archivable_file.id),
    )

    otel.reset()
    await joint_fixture.event_subscriber.run(forever=False)

    assert_recorded_spans(
        otel,
        [
            # Manual spans wrapping the subscriber, translators and core
            "KafkaEventSubscriber._consume_event",
            "EventSubTranslator._consume_file_staging_request",
            "FileRegistry.stage_registered_file",
            "EventPubTranslator.file_staged_for_download",
            # Autoinstrumented Kafka consumer and producer (aiokafka)
            "file-downloads receive",
            "file-stagings send",
            # Autoinstrumented MongoDB lookup (pymongo)
            "test.find",
            # Autoinstrumented object storage (botocore)
            "S3.HeadObject",
            "S3.HeadObject",
            "S3.HeadObject",
            "S3.HeadBucket",
            "S3.CopyObject",
        ],
    )


async def test_publish_events_records_spans(otel, joint_fixture: JointFixture):
    """The outbox-publisher entrypoint reads stored events back from MongoDB and
    re-emits them to Kafka - both autoinstrumented.
    """
    topic = joint_fixture.config.file_internally_registered_topic
    async with get_persistent_publisher(config=joint_fixture.config) as publisher:
        # Seed one stored event so republishing has something to read and re-publish.
        await publisher.publish(
            payload={"test": "event"}, type_="upserted", key="test", topic=topic
        )

        otel.reset()
        await publisher.republish()

    assert_recorded_spans(
        otel,
        [
            # Autoinstrumented MongoDB read (pymongo)
            "test.find",
            # Autoinstrumented Kafka producer (aiokafka)
            "internal-file-registry send",
        ],
    )


async def test_long_running_entrypoints_configure_otel():
    """An entrypoint that skips it emits no traces at all.

    `migrate_db` is excluded by convention: a one-off command, not a service.
    """
    excluded = {"migrate_db"}
    entrypoints = {
        name: obj
        for name, obj in vars(main).items()
        if inspect.iscoroutinefunction(obj) and obj.__module__ == main.__name__
    }
    assert entrypoints, "No entrypoints found - has main.py been restructured?"

    missing = sorted(
        name
        for name, func in entrypoints.items()
        if name not in excluded
        and "configure_opentelemetry" not in inspect.getsource(func)
    )
    assert not missing, f"Entrypoints not configuring OpenTelemetry: {missing}"
