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
#

"""Generate secrets for authenticated and encrypted communication with Kafka."""

import datetime
import ipaddress
import secrets
import string

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID, ObjectIdentifier

__all__ = ["KafkaSecrets"]


class KafkaSecrets:
    """Container for all secrets needed to establish a TLS connection with Kafka."""

    ca_cert: str

    broker_cert: str
    broker_key: str
    broker_pwd: str

    client_cert: str
    client_key: str
    client_pwd: str

    def __init__(
        self,
        hostname: str = "localhost",
        broker_pwd_size: int = 0,
        client_pwd_size: int = 16,
        days: int = 1,
    ) -> None:
        """Generate random secrets in PEM format.

        Unfortunately, the Kafka broker does not support the password protection
        algorithm provided by the cryptography library. Therefore, and because this
        is a feature that we do not need to test here, we do not generate a password
        for the broker key by default. However, is works with the Kafka client.
        """
        ca_cert, ca_key = generate_self_signed_cert(cn="ca.test.dev", days=days)
        self.ca_cert = cert_to_pem(ca_cert)

        cert, key = generate_signed_cert(
            cn=hostname, ca=ca_cert, ca_key=ca_key, client=False, days=days
        )

        self.broker_cert = cert_to_pem(cert)
        password = generate_password(broker_pwd_size)
        self.broker_key = key_to_pem(key, password)
        self.broker_pwd = password

        cert, key = generate_signed_cert(
            cn=hostname, ca=ca_cert, ca_key=ca_key, client=True, days=days
        )

        self.client_cert = cert_to_pem(cert)
        password = generate_password(client_pwd_size)
        self.client_key = key_to_pem(key, password)
        self.client_pwd = password


def cert_to_pem(cert: x509.Certificate) -> str:
    """Serialize the given certificate in PEM format."""
    return cert.public_bytes(serialization.Encoding.PEM).decode("ascii")


def key_to_pem(key: rsa.RSAPrivateKey, password: str | None) -> str:
    """Serialize the given key in PEM format."""
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=get_encryption_algorithm(password),
    ).decode("ascii")


def generate_password(size: int = 16) -> str:
    """Generate a random password."""
    chars = string.ascii_letters + string.digits
    choice = secrets.choice
    return "".join(choice(chars) for _i in range(size))


def get_encryption_algorithm(
    password: str | None,
) -> serialization.KeySerializationEncryption:
    """Get an encryption algorithm for the given password."""
    return (
        serialization.BestAvailableEncryption(password.encode("utf-8"))
        if password
        else serialization.NoEncryption()
    )


def generate_key() -> rsa.RSAPrivateKey:
    """Generate a private key using RSA."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def generate_cert(
    subject: x509.Name,
    issuer: x509.Name,
    public_key: rsa.RSAPublicKey,
    signing_key: rsa.RSAPrivateKey,
    is_ca: bool,
    days: int,
    extended_key_usage: list[ObjectIdentifier],
    issuer_key: rsa.RSAPublicKey,
    san: x509.SubjectAlternativeName | None = None,
) -> x509.Certificate:
    """Generate a certificate with the given parameters."""
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)
        )
        .add_extension(
            x509.BasicConstraints(ca=is_ca, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=is_ca,
                crl_sign=is_ca,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage(extended_key_usage),
            critical=False,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(public_key),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key),
            critical=False,
        )
    )
    if san is not None:
        # Modern TLS verifies the SAN (not the CN); required for hostname/IP matching.
        builder = builder.add_extension(san, critical=False)
    return builder.sign(signing_key, hashes.SHA256())


def docker_bridge_gateway() -> str | None:
    """Best-effort docker default-bridge gateway IP, or None if undeterminable.

    This is the address testcontainers uses to reach mapped container ports under
    docker-in-docker (where `localhost` does not reach them). Determined without a
    running container, so it can be baked into the cert before the broker starts.
    """
    try:
        import docker  # noqa: PLC0415  # lazy: keep gateway lookup best-effort

        config = docker.from_env().networks.get("bridge").attrs["IPAM"]["Config"]
        return config[0]["Gateway"]
    except Exception:
        return None


def san_for_host(host: str) -> x509.SubjectAlternativeName:
    """Build a SubjectAlternativeName covering `host` plus the endpoints testcontainers
    may use to reach the broker.

    Modern TLS verifies the SAN (not the CN), and an IP host must be an IPAddress entry
    rather than a DNSName. testcontainers reaches containers via `localhost` under local
    Docker but via the docker-bridge gateway IP (e.g. 172.17.0.1) under docker-in-docker,
    so cover all of localhost / 127.0.0.1 / the bridge gateway / the requested host.
    """
    candidates = ["localhost", "127.0.0.1", host]
    gateway = docker_bridge_gateway()
    if gateway:
        candidates.append(gateway)

    names: list[x509.GeneralName] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            names.append(x509.IPAddress(ipaddress.ip_address(candidate)))
        except ValueError:
            names.append(x509.DNSName(candidate))
    return x509.SubjectAlternativeName(names)


def generate_signed_cert(
    cn: str,
    ca: x509.Certificate,
    ca_key: rsa.RSAPrivateKey,
    client: bool = False,
    days: int = 1,
) -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
    """Generate a signed certificate with its private key."""
    key = generate_key()
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    cert = generate_cert(
        subject=subject,
        issuer=ca.subject,
        public_key=key.public_key(),
        signing_key=ca_key,
        is_ca=False,
        days=days,
        extended_key_usage=[
            ExtendedKeyUsageOID.CLIENT_AUTH
            if client
            else ExtendedKeyUsageOID.SERVER_AUTH
        ],
        issuer_key=ca_key.public_key(),  # Use the CA's public key
        san=san_for_host(cn),
    )
    return cert, key


def generate_self_signed_cert(
    cn: str, days: int = 1
) -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
    """Generate a self-signed certificate with its private key."""
    key = generate_key()
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    cert = generate_cert(
        subject=subject,
        issuer=issuer,
        public_key=key.public_key(),
        signing_key=key,
        is_ca=True,
        days=days,
        extended_key_usage=[
            ExtendedKeyUsageOID.SERVER_AUTH,
        ],
        issuer_key=key.public_key(),  # Use the same key for self-signed cert
    )
    return cert, key
