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

"""Tests for the transport factory, including SSL verification handling."""

import shutil
import ssl
from pathlib import Path

import certifi
import pytest
from hishel.httpx import AsyncCacheTransport
from httpx import AsyncHTTPTransport

from ghga_service_commons.transports.config import CompositeCacheConfig, CompositeConfig
from ghga_service_commons.transports.factory import (
    CompositeTransportFactory,
    get_ssl_verify,
)
from ghga_service_commons.transports.ratelimiting import AsyncRateLimitingTransport
from ghga_service_commons.transports.retry import AsyncRetryTransport


@pytest.fixture
def ca_bundle(tmp_path: Path) -> Path:
    """Provide a path to a real, loadable CA bundle copied into a temp dir."""
    bundle = tmp_path / "ca-bundle.pem"
    shutil.copyfile(certifi.where(), bundle)
    return bundle


def test_get_ssl_verify_requests_ca_bundle(
    monkeypatch: pytest.MonkeyPatch, ca_bundle: Path
):
    """REQUESTS_CA_BUNDLE set -> returns a loaded SSLContext."""
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(ca_bundle))

    verify = get_ssl_verify()

    assert isinstance(verify, ssl.SSLContext)


def test_get_ssl_verify_ssl_cert_file(monkeypatch: pytest.MonkeyPatch, ca_bundle: Path):
    """SSL_CERT_FILE set (REQUESTS_CA_BUNDLE unset) -> returns a loaded SSLContext."""
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.setenv("SSL_CERT_FILE", str(ca_bundle))

    verify = get_ssl_verify()

    assert isinstance(verify, ssl.SSLContext)


def test_get_ssl_verify_neither_set(monkeypatch: pytest.MonkeyPatch):
    """Neither env var set -> returns True (httpx default = certifi)."""
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)

    verify = get_ssl_verify()

    assert verify is True


def test_get_ssl_verify_requests_ca_bundle_precedence(
    monkeypatch: pytest.MonkeyPatch, ca_bundle: Path, tmp_path: Path
):
    """Both set and both loadable -> REQUESTS_CA_BUNDLE wins over SSL_CERT_FILE.

    Both env vars point to valid, loadable bundles that differ in content, so the
    loaded CA set identifies which file was actually used: the full certifi bundle
    (REQUESTS_CA_BUNDLE) versus a single-cert subset (SSL_CERT_FILE).
    """
    single_cert_bundle = tmp_path / "single-cert.pem"
    marker = "-----END CERTIFICATE-----"
    first_cert = ca_bundle.read_text().split(marker)[0] + marker + "\n"
    single_cert_bundle.write_text(first_cert)

    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(ca_bundle))
    monkeypatch.setenv("SSL_CERT_FILE", str(single_cert_bundle))

    verify = get_ssl_verify()

    assert isinstance(verify, ssl.SSLContext)
    expected = ssl.create_default_context(cafile=str(ca_bundle))
    assert len(verify.get_ca_certs()) == len(expected.get_ca_certs())
    assert len(verify.get_ca_certs()) > 1


def test_create_ratelimiting_retry_transport_layers_transports():
    """Ensure the retry transport wraps a rate limiting transport over an HTTP transport."""
    transport = CompositeTransportFactory.create_ratelimiting_retry_transport(
        CompositeConfig()
    )

    assert isinstance(transport, AsyncRetryTransport)
    ratelimiting = transport._transport
    assert isinstance(ratelimiting, AsyncRateLimitingTransport)
    assert isinstance(ratelimiting._transport, AsyncHTTPTransport)


def test_create_ratelimiting_retry_transport_uses_custom_base():
    """Ensure a provided base transport is used at the bottom of the stack."""
    base = AsyncHTTPTransport()

    transport = CompositeTransportFactory.create_ratelimiting_retry_transport(
        CompositeConfig(), base_transport=base
    )

    ratelimiting = transport._transport
    assert isinstance(ratelimiting, AsyncRateLimitingTransport)
    assert ratelimiting._transport is base


def test_create_cached_ratelimiting_retry_transport_layers_transports():
    """The cache transport wraps the retry and rate limiting transports."""
    transport = CompositeTransportFactory.create_cached_ratelimiting_retry_transport(
        CompositeCacheConfig()
    )

    assert isinstance(transport, AsyncCacheTransport)
    retry = transport.next_transport
    assert isinstance(retry, AsyncRetryTransport)
    assert isinstance(retry._transport, AsyncRateLimitingTransport)
