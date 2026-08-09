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

"""Tests that real service operations record spans, including autoinstrumented ones."""

import base64
import inspect
import os
from collections import Counter

import pytest
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.opentelemetry.testutils import (  # noqa: F401
    otel_fixture,
    otel_provider_fixture,
)

from ekss import main
from ekss.inject import prepare_rest_app
from tests_ekss.fixtures.config import get_config
from tests_ekss.fixtures.keypair import KeypairFixture
from tests_ekss.fixtures.utils import make_secret_payload
from tests_ekss.fixtures.vault import VaultFixture

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


async def test_post_secret_records_spans(
    otel,  # first, so OpenTelemetry is configured before the app is built
    keypair: KeypairFixture,
    vault_fixture: VaultFixture,
):
    """Covers both layers of manual spans - route and Vault - in one real request."""
    _, encrypted_secret = make_secret_payload(keypair.ekss_pk)
    config = get_config([vault_fixture.config, keypair.config])

    otel.reset()
    async with (
        prepare_rest_app(config=config) as app,
        AsyncTestClient(app=app) as client,
    ):
        response = await client.post(url="/secrets", content=encrypted_secret)

    assert response.status_code == 201
    assert response.json()["secret_id"]

    assert_recorded_spans(
        otel,
        [
            # REST server span plus its ASGI receive/send sub-spans
            "POST /secrets",
            "POST /secrets http receive",
            "POST /secrets http receive",
            "POST /secrets http send",
            "POST /secrets http send",
            # Manual spans wrapping the route handler and the Vault call
            "routes.post_encryption_secret",
            "VaultClient.store_secret",
        ],
    )

    server_span = otel.assert_has_span("POST /secrets")
    assert server_span.attributes
    assert server_span.attributes["http.status_code"] == 201

    # The Vault span belongs to the same trace as the request.
    vault_span = otel.assert_has_span("VaultClient.store_secret")
    assert vault_span.context.trace_id == server_span.context.trace_id


async def test_get_envelope_records_spans(
    otel,  # first, so OpenTelemetry is configured before the app is built
    keypair: KeypairFixture,
    vault_fixture: VaultFixture,
):
    """Fetching an envelope records the route span and the Vault retrieval span."""
    secret = os.urandom(32)
    secret_id = vault_fixture.adapter.store_secret(secret=secret)
    client_pk = base64.urlsafe_b64encode(keypair.user_pk).decode("utf-8")
    config = get_config([vault_fixture.config, keypair.config])

    otel.reset()
    async with (
        prepare_rest_app(config=config) as app,
        AsyncTestClient(app=app) as client,
    ):
        response = await client.get(url=f"/secrets/{secret_id}/envelopes/{client_pk}")

    assert response.status_code == 200

    assert_recorded_spans(
        otel,
        [
            # REST server span plus its ASGI send sub-spans
            "GET /secrets/{secret_id}/envelopes/{client_pk}",
            "GET /secrets/{secret_id}/envelopes/{client_pk} http send",
            "GET /secrets/{secret_id}/envelopes/{client_pk} http send",
            # Manual spans wrapping the route handler and the Vault call
            "routes.get_header_envelope",
            "VaultClient.get_secret",
        ],
    )

    # Without the parent link the manual span would be detached from the trace.
    route_span = otel.assert_has_span("routes.get_header_envelope")
    server_span = otel.assert_has_span("GET /secrets/{secret_id}/envelopes/{client_pk}")
    assert route_span.parent is not None
    assert route_span.parent.span_id == server_span.context.span_id


async def test_delete_secret_records_spans(
    otel,  # first, so OpenTelemetry is configured before the app is built
    keypair: KeypairFixture,
    vault_fixture: VaultFixture,
):
    """Deleting a secret records the route span and the Vault deletion span."""
    secret_id = vault_fixture.adapter.store_secret(secret=os.urandom(32))
    config = get_config([vault_fixture.config, keypair.config])

    otel.reset()
    async with (
        prepare_rest_app(config=config) as app,
        AsyncTestClient(app=app) as client,
    ):
        response = await client.delete(url=f"/secrets/{secret_id}")

    assert response.status_code == 204

    assert_recorded_spans(
        otel,
        [
            # REST server span plus its ASGI send sub-spans
            "DELETE /secrets/{secret_id}",
            "DELETE /secrets/{secret_id} http send",
            "DELETE /secrets/{secret_id} http send",
            # Manual spans wrapping the route handler and the Vault call
            "routes.delete_secret",
            "VaultClient.delete_secret",
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
