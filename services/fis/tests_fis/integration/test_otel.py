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
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Any

import pytest
import pytest_asyncio

from fis.cli import cli
from fis.config import Config
from fis.constants import DHFS_USER_AGENT_PREFIX, GHGA
from fis.inject import (
    get_persistent_publisher,
    prepare_core,
    prepare_event_subscriber,
    prepare_rest_app,
)
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils.jwt_helpers import (
    generate_jwk,
    sign_and_serialize_token,
)
from hexkit.opentelemetry.testutils import (  # noqa: F401
    otel_fixture,
    otel_provider_fixture,
)
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture
from tests_fis.fixtures.config import get_config
from tests_fis.fixtures.utils import create_file_under_interrogation

pytestmark = pytest.mark.asyncio()

HUB = "HUB1"
USER_AGENT = f"{DHFS_USER_AGENT_PREFIX}/2.0.0"


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


@dataclass
class OtelRig:
    """A joint setup built with a signing key the test controls."""

    config: Config
    rest_client: AsyncTestClient
    outbox_consumer: object
    auth_header: dict[str, str]


@pytest_asyncio.fixture()
async def rig(
    otel,  # first, so OpenTelemetry is configured before the app is built
    kafka: KafkaFixture,
    mongodb: MongoDbFixture,
) -> AsyncGenerator[OtelRig]:
    """Build the service against a data hub key this test can sign tokens with.

    The shared `joint_fixture` uses config-file keys whose private halves are absent.
    """
    jwk = generate_jwk()
    config = get_config(
        sources=[kafka.config, mongodb.config],
        data_hub_auth_keys={HUB: jwk.export_public()},
    )
    token = sign_and_serialize_token(
        claims={"iss": GHGA, "aud": GHGA, "sub": HUB}, key=jwk, valid_seconds=60
    )

    async with (
        prepare_core(config=config) as interrogation_handler,
        prepare_rest_app(config=config, core_override=interrogation_handler) as app,
        prepare_event_subscriber(
            config=config, core_override=interrogation_handler
        ) as outbox_consumer,
        AsyncTestClient(app=app) as rest_client,
    ):
        yield OtelRig(
            config=config,
            rest_client=rest_client,
            outbox_consumer=outbox_consumer,
            auth_header={
                "Authorization": f"Bearer {token}",
                "User-Agent": USER_AGENT,
            },
        )


async def test_list_uploads_records_spans(otel, rig: OtelRig):
    """One authenticated call should produce route, server and MongoDB spans."""
    otel.reset()
    response = await rig.rest_client.get(
        f"/storages/{HUB}/uploads", headers=rig.auth_header
    )
    assert response.status_code == 200

    assert_recorded_spans(
        otel,
        [
            # Manual span wrapping the route handler
            "routes.list_uploads",
            # REST server span plus its ASGI send sub-spans
            "GET /storages/{storage_alias}/uploads",
            "GET /storages/{storage_alias}/uploads http send",
            "GET /storages/{storage_alias}/uploads http send",
            # Autoinstrumented MongoDB lookup (pymongo)
            "test.find",
        ],
    )

    server_span = otel.assert_has_span("GET /storages/{storage_alias}/uploads")
    assert server_span.attributes
    assert server_span.attributes["http.status_code"] == 200

    # Without the parent link the manual span would be detached from the trace.
    route_span = otel.assert_has_span("routes.list_uploads")
    assert route_span.parent is not None
    assert route_span.parent.span_id == server_span.context.span_id


async def test_outbox_consumption_records_spans(
    otel, rig: OtelRig, kafka: KafkaFixture
):
    """Event consumption is a separate entry point from the REST API."""
    file = create_file_under_interrogation(HUB)
    file.state = "inbox"
    await kafka.publish_event(
        payload=file.model_dump(),
        type_="upserted",
        topic=rig.config.file_upload_topic,
        key=str(file.id),
    )

    otel.reset()
    await rig.outbox_consumer.run(forever=False)  # type: ignore[attr-defined]

    assert_recorded_spans(
        otel,
        [
            # Manual span wrapping the subscriber
            "KafkaEventSubscriber._consume_event",
            # Autoinstrumented Kafka consumer (aiokafka)
            "file-uploads receive",
            # Autoinstrumented MongoDB write (pymongo)
            "test.insert",
        ],
    )


async def test_publish_events_records_spans(otel, rig: OtelRig):
    """The outbox-publisher entrypoint reads stored events back from MongoDB and
    re-emits them to Kafka - both autoinstrumented.
    """
    topic = rig.config.file_interrogations_topic
    async with get_persistent_publisher(config=rig.config) as publisher:
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
            "file-interrogations send",
        ],
    )


def configures_otel(command: Callable[..., Any]) -> bool:
    """Tell whether a command runs a coroutine that calls `configure_opentelemetry`.

    It reads the names the code refers to, since running the command starts the service.
    """
    return any(
        "configure_opentelemetry" in inspect.getclosurevars(func).globals
        for func in inspect.getclosurevars(command).globals.values()
        if inspect.iscoroutinefunction(func)
    )


async def test_long_running_commands_configure_otel():
    """A command that skips it emits no traces at all.

    `migrate-db` is excluded by convention: a one-off command, not a service.
    """
    commands = {
        info.name or info.callback.__name__: info.callback
        for info in cli.registered_commands
        if info.callback and info.name != "migrate-db"
    }
    missing = sorted(
        name for name, callback in commands.items() if not configures_otel(callback)
    )
    assert not missing, f"Commands not configuring OpenTelemetry: {missing}"
