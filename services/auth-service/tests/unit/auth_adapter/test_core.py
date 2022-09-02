# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

import logging

from jwcrypto import jwk

from auth_service.auth_adapter.core.auth import (
    decode_and_verify_token,
    exchange_token,
    sign_and_encode_token,
)
from auth_service.auth_adapter.core.jwks import external_jwks, internal_jwk

from ...fixtures import (  # noqa: F401; pylint: disable=unused-import
    fixture_external_key,
)


def test_external_jwks():
    """Test that an external JWK set is provided with more than one key."""
    assert isinstance(external_jwks, jwk.JWKSet)
    jwks_dict = external_jwks.export(private_keys=False, as_dict=True)
    assert "keys" in jwks_dict
    keys = jwks_dict["keys"]
    assert keys
    assert isinstance(keys, list)
    assert len(keys) > 1
    for key in keys:
        assert "kty" in key
        assert key["kty"] in ("EC", "RSA")
        assert "use" in key
        assert key["use"] == "sig"


def test_internal_jwk():
    """Test that an internal JWK set is provided."""
    assert isinstance(internal_jwk, jwk.JWK)
    key = internal_jwk.export(as_dict=True)
    assert "kty" in key
    assert key["kty"] in ("EC", "RSA")


def test_checks_signature_of_access_token(caplog):
    """Test that the signature of an access token is verified."""
    caplog.set_level(logging.DEBUG)
    access_token = (
        "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWV9."
        "EkN-DOsnsuRjRO6BxXemmJDm3HbxrbRzXglbN2S4sOkopdU4IsDxTI8jO19W_A4K8ZPJi"
        "jNLis4EZsHeY559a4DFOd50_OqgHGuERTqYZyuhtF39yxJPAjUESwxk2J5k_4zM3O-vtd"
        "1Ghyo4IbqKKSy6J9mTniYJPenn5-HIirE"
    )
    assert decode_and_verify_token(access_token) is None
    key = jwk.JWK.from_pem(
        "-----BEGIN PUBLIC KEY-----\n"
        "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDdlatRjRjogo3WojgGHFHYLugdUWAY9iR3"
        "fy4arWNA1KoS8kVw33cJibXr8bvwUAUparCwlvdbH6dvEOfou0/gCFQsHUfQrSDv+MuSUMAe"
        "8jzKE4qW+jK+xQU9a03GUnKHkkle+Q0pX/g6jXZ7r1/xAK5Do2kQ+X5xK9cipRgEKwIDAQAB\n"
        "-----END PUBLIC KEY-----".encode("ascii")
    )
    payload = decode_and_verify_token(access_token, key=key)
    assert payload == {"admin": True, "name": "John Doe", "sub": "1234567890"}
    access_token = ".".join(access_token.split(".")[:-1] + ["aW52YWxpZCBzaWduYXR1cmU"])
    assert decode_and_verify_token(access_token, key=key) is None
    assert [rec.message for rec in caplog.records] == [
        "Signature key for access token not found",
        "Invalid access token signature",
    ]


def test_does_not_verify_access_token_with_invalid_format(caplog):
    """Test that access tokens with invalid format are not verified."""
    caplog.set_level(logging.DEBUG)
    assert decode_and_verify_token(None) is None
    assert decode_and_verify_token("Not a JWT") is None
    assert decode_and_verify_token("ab.cde.fg") is None
    assert decode_and_verify_token("aGVhZGVy.cGF5bG9hZA.c2lnbmF0dXJl") is None
    assert len(caplog.record_tuples) == 3
    assert all(rec.message == "Invalid access token format" for rec in caplog.records)


def test_does_not_verify_token_with_invalid_payload(caplog):
    """Test that access tokens with invalid payload are not verified."""
    caplog.set_level(logging.DEBUG)
    key = jwk.JWK(kty="oct", k="r0TSf_aAU9eS7I5JPPJ20pmkPmR__9LsfnZaKfXZYp8")
    token_with_valid_payload = (
        "eyJhbGciOiJIUzI1NiJ9."
        "eyJzdWIiOiAiSm9obiBEb2UifQ."
        "RQYHxFwGjMdVh-umuuA1Yd4Ssx6TAYkg1INYK6_lKVw"
    )
    assert decode_and_verify_token(token_with_valid_payload, key=key) == {
        "sub": "John Doe"
    }
    token_with_text_as_payload = (
        "eyJhbGciOiJIUzI1NiJ9."
        "VGhpcyBpcyBub3QgSlNPTiE."
        "bKt6NQoZGLOLqqqB-XT99ENnsmv-hxLId08FxR4LUOw"
    )
    assert decode_and_verify_token(token_with_text_as_payload, key=key) is None
    token_with_bad_encoding = (
        "eyJhbGciOiJIUzI1NiJ9."
        "eyJzdWIiOiAiRnLpZOlyaWMgQ2hvcGluIn0."
        "8OTfVB6CN2pXgPHZBPdbkqWGd2XhtbVDhlcYdYNh6d4"
    )
    assert decode_and_verify_token(token_with_bad_encoding, key=key) is None
    assert [rec.message for rec in caplog.records] == [
        "Access token payload is not valid JSON",
        "Access token payload has invalid encoding",
    ]


def test_verifies_access_token_with_rsa_signature():
    """Test that an access tokens with RSA signature can be verified."""
    key = jwk.JWK.from_pem(
        "-----BEGIN PUBLIC KEY-----\n"
        "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu1SU1LfVLPHCozMxH2Mo"
        "4lgOEePzNm0tRgeLezV6ffAt0gunVTLw7onLRnrq0/IzW7yWR7QkrmBL7jTKEn5u"
        "+qKhbwKfBstIs+bMY2Zkp18gnTxKLxoS2tFczGkPLPgizskuemMghRniWaoLcyeh"
        "kd3qqGElvW/VDL5AaWTg0nLVkjRo9z+40RQzuVaE8AkAFmxZzow3x+VJYKdjykkJ"
        "0iT9wCS0DRTXu269V264Vf/3jvredZiKRkgwlL9xNAwxXFg0x/XFw005UWVRIkdg"
        "cKWTjpBP2dPwVZ4WWC+9aGVd+Gyn1o0CLelf4rEjGoXbAAEgAqeGUxrcIlbjXfbc"
        "mwIDAQAB\n"
        "-----END PUBLIC KEY-----".encode("ascii")
    )
    access_token = (
        "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRy"
        "dWUsImlhdCI6MTUxNjIzOTAyMn0."
        "NHVaYe26MbtOYhSKkoKYdFVomg4i8ZJd8_-RU8VNbftc4TSMb4bXP3l3YlNWACwy"
        "XPGffz5aXHc6lty1Y2t4SWRqGteragsVdZufDn5BlnJl9pdR_kdVFUsra2rWKEof"
        "kZeIC4yWytE58sMIihvo9H1ScmmVwBcQP6XETqYd0aSHp1gOa9RdUPDvoXQ5oqyg"
        "TqVtxaDr6wUFKrKItgBMzWIdNZ6y7O9E0DhEPTbE9rfBo6KTFsHAZnMg4k68CDp2"
        "woYIaXbmYTWcvbzIuHO7_37GT79XdIwkm95QJ7hYC9RiwrV7mesbY4PAahERJawn"
        "tho0my942XheVLmGwLMBkQ"
    )
    assert decode_and_verify_token(access_token, key=key) == {
        "sub": "1234567890",
        "name": "John Doe",
        "admin": True,
        "iat": 1516239022,
    }


def test_verifies_access_token_with_ec_signature():
    """Test that access tokens with EC signature can be verified."""
    key = jwk.JWK.from_pem(
        "-----BEGIN PUBLIC KEY-----\n"
        "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAERqVXn+o+6zEOpWEsGw5CsB+wd8zO"
        "jxu0uASGpiGP+wYfcc1unyMxcStbDzUjRuObY8DalaCJ9/J6UrkQkZBtZw==\n"
        "-----END PUBLIC KEY-----".encode("ascii")
    )
    access_token = (
        "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRta"
        "W4iOnRydWUsImlhdCI6MTY2MTYyMTc0OSwiZXhwIjoxNjYxNjI1MzQ5fQ."
        "k29jHcEkyFvnf1P5rcEEOiMBIGmOwSBmb1tBiEyYcITP3122IZrQlO3ca"
        "e9ZvPlDdgK_g95LB9jPNz5R2DU6XQ"
    )
    assert decode_and_verify_token(access_token, key=key) == {
        "sub": "1234567890",
        "name": "John Doe",
        "admin": True,
        "iat": 1661621749,
        "exp": 1661625349,
    }


def test_signs_internal_token():
    """Test that internal tokens can be signed."""
    payload = {"foo": "bar"}
    token = sign_and_encode_token(payload)
    assert isinstance(token, str)
    assert token.count(".") == 2
    assert decode_and_verify_token(token, key=internal_jwk) == payload


def test_token_exchange(external_key):
    """Test that a valid external token is exchanged against an internal token."""
    ext_payload = {"name": "Foo Bar", "mail": "foo@bar", "sub": "foo", "iss": "bar"}
    access_token = sign_and_encode_token(ext_payload, key=external_key)
    internal_token = exchange_token(access_token)
    assert isinstance(internal_token, str)
    assert internal_token.count(".") == 2
    int_payload = decode_and_verify_token(internal_token, key=internal_jwk)
    assert int_payload == {"name": "Foo Bar", "mail": "foo@bar"}
