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
from hexkit.opentelemetry.testutils import (  # noqa: F401
    otel_fixture,
    otel_provider_fixture,
)
from httpx import Headers

from pcs import main
from pcs.inject import get_persistent_publisher
from tests_pcs.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio()

TEST_FILE_ID = UUID("70a7e795-fe0c-4a03-9af4-a758f5b5464b")


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


async def test_deletion_request_records_spans_for_all_backends(
    otel,  # first, so OpenTelemetry is configured before the fixtures below
    joint_fixture: JointFixture,
):
    """One request should produce REST, MongoDB and Kafka spans."""
    otel.reset()
    headers = Headers({"Authorization": f"Bearer {joint_fixture.token}"})
    response = await joint_fixture.rest_client.delete(
        f"/files/{TEST_FILE_ID}", headers=headers, timeout=5
    )
    assert response.status_code == 202

    assert_recorded_spans(
        otel,
        [
            # REST server span plus its ASGI send sub-spans (no body, so no receive)
            "DELETE /files/{file_id}",
            "DELETE /files/{file_id} http send",
            "DELETE /files/{file_id} http send",
            # Manual span wrapping the route handler
            "routes.delete_file",
            # Autoinstrumented MongoDB writes (pymongo)
            "test.update",
            "test.update",
            # Autoinstrumented Kafka producer (aiokafka)
            "file-deletion-requests send",
        ],
    )

    server_span = otel.assert_has_span("DELETE /files/{file_id}")
    assert server_span.attributes
    assert server_span.attributes["http.status_code"] == 202

    # Without the parent link the manual span would be detached from the trace.
    route_span = otel.assert_has_span("routes.delete_file")
    assert route_span.parent is not None
    assert route_span.parent.span_id == server_span.context.span_id
    assert route_span.context.trace_id == server_span.context.trace_id


async def test_publish_events_records_spans(otel, joint_fixture: JointFixture):
    """The outbox-publisher entrypoint reads stored events back from MongoDB and
    re-emits them to Kafka - both autoinstrumented.
    """
    topic = joint_fixture.config.file_deletion_request_topic
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
            "file-deletion-requests send",
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
