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

"""Tests that real service operations record spans across all instrumented backends."""

import inspect
from collections import Counter
from uuid import UUID

import pytest

from ghga_event_schemas.pydantic_ import FileDeletionRequested
from hexkit.correlation import new_correlation_id, set_correlation_id
from hexkit.opentelemetry.testutils import (  # noqa: F401
    otel_fixture,
    otel_provider_fixture,
)
from hexkit.utils import now_utc_ms_prec
from tests_ucs.fixtures import utils
from tests_ucs.fixtures.joint import JointFixture
from ucs import main
from ucs.inject import prepare_outbox_publisher

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


async def _create_box(joint_fixture: JointFixture) -> UUID:
    """Create a FileUploadBox through the REST API and return its ID."""
    token_header = utils.create_file_box_token_header(jwk=joint_fixture.rs_jwk)
    response = await joint_fixture.rest_client.post(
        "/boxes",
        json={"storage_alias": "test", "max_size": utils.TEST_MAX_BOX_SIZE},
        headers=token_header,
    )
    assert response.status_code == 201
    return UUID(response.json())


async def test_box_creation_records_spans_for_all_backends(
    otel,  # first, so OpenTelemetry is configured before the fixtures below
    joint_fixture: JointFixture,
):
    """One request should produce REST, MongoDB and Kafka spans, plus the manual one."""
    otel.reset()
    box_id = await _create_box(joint_fixture)
    assert box_id  # the flow really did complete

    assert_recorded_spans(
        otel,
        [
            # REST server span plus its ASGI receive/send sub-spans
            "POST /boxes",
            "POST /boxes http receive",
            "POST /boxes http receive",
            "POST /boxes http send",
            "POST /boxes http send",
            # Manual span wrapping the route handler
            "routes.create_box",
            # Autoinstrumented MongoDB writes (pymongo)
            "test.insert",
            "test.update",
            # Autoinstrumented Kafka producer (aiokafka)
            "file-upload-boxes send",
        ],
    )

    server_span = otel.assert_has_span("POST /boxes")
    assert server_span.attributes
    assert server_span.attributes["http.status_code"] == 201

    # Without the parent link the manual span would be detached from the trace.
    route_span = otel.assert_has_span("routes.create_box")
    assert route_span.parent is not None
    assert route_span.parent.span_id == server_span.context.span_id
    assert route_span.context.trace_id == server_span.context.trace_id


async def test_file_upload_creation_records_s3_spans(
    otel,  # first, so OpenTelemetry is configured before the fixtures below
    joint_fixture: JointFixture,
):
    """The only flow that reaches object storage, so it covers botocore."""
    box_id = await _create_box(joint_fixture)

    otel.reset()
    token_header = utils.create_file_token_header(
        jwk=joint_fixture.wps_jwk, box_id=box_id, alias="test_file"
    )
    response = await joint_fixture.rest_client.post(
        f"/boxes/{box_id}/uploads",
        json={
            "alias": "test_file",
            "decrypted_size": utils.DECRYPTED_SIZE,
            "encrypted_size": utils.ENCRYPTED_SIZE,
            "part_size": utils.PART_SIZE,
        },
        headers=token_header,
    )
    assert response.status_code == 201

    assert_recorded_spans(
        otel,
        [
            # REST server span plus its ASGI receive/send sub-spans
            "POST /boxes/{box_id}/uploads",
            "POST /boxes/{box_id}/uploads http receive",
            "POST /boxes/{box_id}/uploads http receive",
            "POST /boxes/{box_id}/uploads http send",
            "POST /boxes/{box_id}/uploads http send",
            # Manual span wrapping the route handler
            "routes.create_file_upload",
            # Autoinstrumented MongoDB access (pymongo)
            "test.find",
            "test.find",
            "test.insert",
            "test.update",
            "test.update",
            # Autoinstrumented object storage (botocore)
            "S3.ListMultipartUploads",
            "S3.CreateMultipartUpload",
            # Autoinstrumented Kafka producer (aiokafka)
            "file-uploads send",
        ],
    )


async def test_consumed_event_records_spans(
    otel,  # first, so OpenTelemetry is configured before the fixtures below
    joint_fixture: JointFixture,
):
    """Event consumption is a separate entry point from the REST API."""
    box_id = await _create_box(joint_fixture)

    event = FileDeletionRequested(file_id=box_id, created=now_utc_ms_prec())
    await joint_fixture.kafka.publish_event(
        payload=event.model_dump(mode="json"),
        type_=joint_fixture.config.file_deletion_request_type,
        topic=joint_fixture.config.file_deletion_request_topic,
        key=str(box_id),
    )

    otel.reset()
    async with set_correlation_id(new_correlation_id()):
        await joint_fixture.event_subscriber.run(forever=False)

    assert_recorded_spans(
        otel,
        [
            # Manual spans wrapping the subscriber and the translator
            "KafkaEventSubscriber._consume_event",
            "EventSubTranslator._consume_file_deletion_requested",
            # Autoinstrumented Kafka consumer (aiokafka)
            "file-deletion-requests receive",
            # Autoinstrumented MongoDB lookup (pymongo)
            "test.find",
        ],
    )


async def test_publish_events_records_spans(
    otel,  # first, so OpenTelemetry is configured before the fixtures below
    joint_fixture: JointFixture,
):
    """The outbox-publisher entrypoint reads stored records back from MongoDB and
    re-emits them to Kafka - both autoinstrumented.
    """
    await _create_box(joint_fixture)  # persists a FileUploadBox via the outbox

    otel.reset()
    async with prepare_outbox_publisher(config=joint_fixture.config) as publisher:
        box_dao = await publisher.get_file_upload_box_dao()
        await box_dao.republish()

    assert_recorded_spans(
        otel,
        [
            # Autoinstrumented MongoDB read (pymongo)
            "test.find",
            "test.update",
            # Autoinstrumented Kafka producer (aiokafka)
            "file-upload-boxes send",
        ],
    )


async def test_stale_upload_cleanup_records_spans(
    otel,  # first, so OpenTelemetry is configured before the fixtures below
    joint_fixture: JointFixture,
):
    """The stale-upload cleanup entrypoint reaches both MongoDB and object storage."""
    otel.reset()
    async with set_correlation_id(new_correlation_id()):
        await joint_fixture.upload_controller.cleanup_stale_uploads()

    assert_recorded_spans(
        otel,
        [
            # Autoinstrumented MongoDB access (pymongo)
            "test.find",
            "test.find",
            # Autoinstrumented object storage (botocore)
            "S3.ListMultipartUploads",
            "S3.ListObjects",
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
