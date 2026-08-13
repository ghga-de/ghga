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

import base64
import inspect
import json
from collections import Counter
from uuid import uuid4

import httpx2
import pytest
from opentelemetry.instrumentation.httpx import HTTPX2ClientInstrumentor
from opentelemetry.trace import SpanKind

from dcs import main
from dcs.adapters.outbound.http.api_calls import get_configured_httpx_client
from dcs.adapters.outbound.http.secrets import SecretsClient
from dcs.inject import get_persistent_publisher
from ghga_event_schemas.pydantic_ import FileInternallyRegistered
from hexkit.opentelemetry.testutils import (  # noqa: F401
    otel_fixture,
    otel_provider_fixture,
)
from hexkit.providers.s3.testutils import FileObject, tmp_file  # noqa: F401
from hexkit.utils import now_utc_ms_prec
from tests_dcs.fixtures.ekss_api import SECRET_ID, EkssApiMock
from tests_dcs.fixtures.joint import CleanupFixture, JointFixture, PopulatedFixture
from tests_dcs.fixtures.utils import generate_work_order_token

pytestmark = pytest.mark.asyncio

ACCESSION = "GHGA001"


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


def _authorize(populated_fixture: PopulatedFixture) -> None:
    """Put a valid work order token on the fixture's REST client."""
    joint_fixture = populated_fixture.joint_fixture
    token = generate_work_order_token(
        file_id=populated_fixture.example_file.file_id,
        accession=ACCESSION,
        jwk=joint_fixture.jwk,
        valid_seconds=120,
    )
    joint_fixture.rest_client.headers = httpx2.Headers(
        {"Authorization": f"Bearer {token}"}
    )


async def test_file_registration_records_spans(
    otel,  # first, so OpenTelemetry is configured before the fixtures below
    joint_fixture: JointFixture,
):
    """Consuming a registration event stores the DRS object and republishes it.

    The event is published before the reset, so only the consume-register-publish
    flow is captured - not the fixture's one-off bucket and collection setup.
    """
    registration_event = FileInternallyRegistered(
        file_id=uuid4(),
        storage_alias=joint_fixture.endpoint_aliases.valid_node,
        bucket_id=joint_fixture.bucket_id,
        archive_date=now_utc_ms_prec(),
        decrypted_size=1234,
        decrypted_sha256="0" * 64,
        encrypted_size=1234567,
        part_size=1,
        encrypted_parts_md5=["some", "checksum"],
        encrypted_parts_sha256=["some", "checksum"],
        secret_id=SECRET_ID,
    )
    await joint_fixture.kafka.publish_event(
        payload=json.loads(registration_event.model_dump_json()),
        type_=joint_fixture.config.file_internally_registered_type,
        topic=joint_fixture.config.file_internally_registered_topic,
    )

    otel.reset()
    await joint_fixture.event_subscriber.run(forever=False)

    assert_recorded_spans(
        otel,
        [
            # Manual spans wrapping the subscriber, translator and publisher
            "EventSubTranslator._consume_files_to_register",
            "EventPubTranslator.file_registered",
            "KafkaEventSubscriber._consume_event",
            # Autoinstrumented MongoDB access (pymongo)
            "test.find",
            "test.insert",
            "test.update",
            "test.update",
            # Autoinstrumented Kafka consumer and producer (aiokafka)
            "internal-file-registry receive",
            "file-downloads send",
        ],
    )


async def test_drs_object_access_records_spans(
    otel,  # first, so OpenTelemetry is configured before the fixtures below
    populated_fixture: PopulatedFixture,
    tmp_file: FileObject,  # noqa: F811
):
    """First request publishes a staging request; the second reaches object storage."""
    joint_fixture = populated_fixture.joint_fixture
    drs_object = await populated_fixture.mongodb_dao.get_by_id(
        populated_fixture.example_file.file_id
    )
    _authorize(populated_fixture)

    otel.reset()
    response = await joint_fixture.rest_client.get(f"/objects/{ACCESSION}", timeout=5)
    assert response.status_code == 202

    # The object is not staged yet, so this request publishes a staging request.
    assert_recorded_spans(
        otel,
        [
            # Manual spans wrapping the route handler, core and publisher
            "routes.get_drs_object",
            "DataRepository._get_access_model",
            "EventPubTranslator.nonstaged_file_requested",
            # REST server span plus its ASGI send sub-spans
            "GET /objects/{object_id}",
            "GET /objects/{object_id} http send",
            "GET /objects/{object_id} http send",
            # Autoinstrumented MongoDB lookup (pymongo)
            "test.find",
            # Autoinstrumented object storage existence check (botocore)
            "S3.HeadObject",
            "S3.HeadBucket",
            # Autoinstrumented Kafka producer (aiokafka)
            "staging-requests send",
        ],
    )

    # Stage the object so the retry actually builds a presigned URL
    file_object = tmp_file.model_copy(
        update={
            "bucket_id": joint_fixture.bucket_id,
            "object_id": str(drs_object.object_id),
        }
    )
    await joint_fixture.s3.populate_file_objects([file_object])

    otel.reset()
    response = await joint_fixture.rest_client.get(f"/objects/{ACCESSION}")
    assert response.status_code == 200

    # The object is staged now, so this request builds a presigned URL and serves it.
    assert_recorded_spans(
        otel,
        [
            # Manual spans wrapping the route handler, core and publisher
            "routes.get_drs_object",
            "DataRepository._get_access_model",
            "EventPubTranslator.download_served",
            # REST server span plus its ASGI send sub-spans
            "GET /objects/{object_id}",
            "GET /objects/{object_id} http send",
            "GET /objects/{object_id} http send",
            # Autoinstrumented MongoDB access (pymongo)
            "test.find",
            "test.update",
            "test.update",
            "test.update",
            # Autoinstrumented object storage existence check (botocore)
            "S3.HeadObject",
            # Autoinstrumented Kafka producer (aiokafka)
            "file-downloads send",
        ],
    )


async def test_envelope_request_records_outbound_http_spans(
    otel,  # first, so OpenTelemetry is configured before the fixtures below
    populated_fixture: PopulatedFixture,
):
    """The only flow that leaves the service over HTTP."""
    joint_fixture = populated_fixture.joint_fixture
    _authorize(populated_fixture)

    otel.reset()
    response = await joint_fixture.rest_client.get(
        f"/objects/{ACCESSION}/envelopes", timeout=5
    )
    assert response.status_code == 200

    # No httpx2 client span here: the mock replaces the transport the instrumentation
    # wraps (see test_outbound_ekss_call_records_httpx_client_span for that span).
    assert_recorded_spans(
        otel,
        [
            # Manual spans wrapping the route handler and the outbound call
            "routes.get_envelope",
            "api_calls.get_envelope_from_ekss",
            # REST server span plus its ASGI send sub-spans
            "GET /objects/{object_id}/envelopes",
            "GET /objects/{object_id}/envelopes http send",
            "GET /objects/{object_id}/envelopes http send",
            # Autoinstrumented MongoDB lookup (pymongo)
            "test.find",
        ],
    )


async def test_outbound_ekss_call_records_httpx_client_span(
    otel,  # first, so OpenTelemetry is configured before the fixtures below
    populated_fixture: PopulatedFixture,
):
    """The outbound EKSS call is autoinstrumented at the client level.

    The global httpx2 autoinstrumentation only wraps the real network transport, which
    the HTTP mock swaps out - so the test above cannot see the outbound span. Here the
    client instance is instrumented directly, the same wrapping hexkit's
    autoinstrumentation applies to the real transport in production, which lets the
    span surface even against the mock.
    """
    config = populated_fixture.joint_fixture.config
    receiver_public_key = base64.b64encode(b"test-public-key").decode()
    ekss = EkssApiMock(config=config)

    async with get_configured_httpx_client(
        config=config, base_transport=ekss.as_transport(), mount_env_proxies=False
    ) as client:
        HTTPX2ClientInstrumentor.instrument_client(client)
        try:
            secrets_client = SecretsClient(config=config, httpx_client=client)

            otel.reset()
            envelope = await secrets_client.get_envelope(
                secret_id=SECRET_ID, receiver_public_key=receiver_public_key
            )
        finally:
            HTTPX2ClientInstrumentor.uninstrument_client(client)

    assert envelope  # the mocked EKSS really answered

    assert_recorded_spans(
        otel,
        [
            # Manual span wrapping the outbound call
            "api_calls.get_envelope_from_ekss",
            # Autoinstrumented outbound HTTP client span (named after the method)
            "GET",
        ],
    )

    manual_span = otel.assert_has_span("api_calls.get_envelope_from_ekss")
    client_span = otel.assert_has_span("GET")
    assert client_span.kind == SpanKind.CLIENT

    # It nests under the manual span, so both belong to the same trace.
    assert client_span.parent is not None
    assert client_span.parent.span_id == manual_span.context.span_id
    assert client_span.context.trace_id == manual_span.context.trace_id


async def test_publish_events_records_spans(
    otel,  # first, so OpenTelemetry is configured before the fixtures below
    joint_fixture: JointFixture,
):
    """The outbox-publisher entrypoint reads stored events back from MongoDB and
    re-emits them to Kafka - both autoinstrumented.
    """
    topic = joint_fixture.config.file_registered_for_download_topic
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
            "file-downloads send",
        ],
    )


async def test_download_bucket_cleaner_records_spans(
    otel,  # first, so OpenTelemetry is configured before the fixtures below
    cleanup_fixture: CleanupFixture,
):
    """The bucket-cleaner entrypoint reaches both object storage and MongoDB."""
    otel.reset()
    await cleanup_fixture.bucket_cleaner.cleanup_download_buckets(
        object_storages_config=cleanup_fixture.config
    )

    assert_recorded_spans(
        otel,
        [
            # Autoinstrumented MongoDB access (pymongo)
            "test.find",
            "test.find",
            # Autoinstrumented object storage (botocore)
            "S3.ListObjects",
            "S3.DeleteObject",
        ],
    )

    # The expired object really was removed, so the flow did its work.
    expired_object = await cleanup_fixture.mongodb_dao.get_by_id(
        cleanup_fixture.expired_file_id
    )
    assert not await cleanup_fixture.s3.storage.does_object_exist(
        bucket_id=cleanup_fixture.bucket_id, object_id=str(expired_object.object_id)
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
