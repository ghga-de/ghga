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

import ssl
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from httpx2 import AsyncHTTPTransport

from ghga_service_commons.transports.config import CompositeConfig
from ghga_service_commons.transports.factory import (
    CompositeTransportFactory,
    get_ssl_verify,
)
from ghga_service_commons.transports.ratelimiting import AsyncRateLimitingTransport
from ghga_service_commons.transports.retry import AsyncRetryTransport

CA_BUNDLE_CERT_COUNT = 3


def throwaway_ca_pem(common_name: str) -> bytes:
    """Generate a throwaway, self-signed CA certificate as PEM bytes."""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return certificate.public_bytes(serialization.Encoding.PEM)


@pytest.fixture
def ca_bundle(tmp_path: Path) -> Path:
    """Provide a loadable CA bundle of several throwaway certificates."""
    bundle = tmp_path / "ca-bundle.pem"
    bundle.write_bytes(
        b"".join(
            throwaway_ca_pem(f"Test CA {number}")
            for number in range(CA_BUNDLE_CERT_COUNT)
        )
    )
    return bundle


@pytest.fixture
def single_cert_bundle(tmp_path: Path) -> Path:
    """Provide a loadable CA bundle holding exactly one throwaway certificate."""
    bundle = tmp_path / "single-cert.pem"
    bundle.write_bytes(throwaway_ca_pem("Test CA single"))
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
    """Neither env var set -> returns True, leaving httpx2 its own default.

    That default is the OS trust store via truststore, not certifi as in httpx 0.x.
    """
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)

    verify = get_ssl_verify()

    assert verify is True


def test_get_ssl_verify_requests_ca_bundle_precedence(
    monkeypatch: pytest.MonkeyPatch, ca_bundle: Path, single_cert_bundle: Path
):
    """Both set and both loadable -> REQUESTS_CA_BUNDLE wins over SSL_CERT_FILE.

    Both env vars point to valid, loadable bundles that differ in the number of
    certificates they hold, so the loaded CA set identifies which file was actually
    used: the multi-cert bundle (REQUESTS_CA_BUNDLE) or the single-cert one
    (SSL_CERT_FILE).
    """
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(ca_bundle))
    monkeypatch.setenv("SSL_CERT_FILE", str(single_cert_bundle))

    verify = get_ssl_verify()

    assert isinstance(verify, ssl.SSLContext)
    assert len(verify.get_ca_certs()) == CA_BUNDLE_CERT_COUNT


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
