# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test the core TOTP functionality."""

import base64
import hashlib
from datetime import timedelta
from random import randint

import pytest
from ghga_service_commons.utils.utc_dates import UTCDatetime, now_as_utc
from pydantic import AnyUrl, SecretStr

from auth_service.auth_adapter.core.totp import (
    TOTPAlgorithm,
    TOTPConfig,
    TOTPHandler,
    TOTPToken,
)


@pytest.fixture(name="totp_handler")
def create_totp_handler() -> TOTPHandler:
    """Create a default TOTP handler."""
    encryption_key = TOTPHandler.random_encryption_key()
    config = TOTPConfig(
        totp_issuer="Test Issuer",
        totp_image=AnyUrl("https://www.test.dev/logo.png"),
        totp_encryption_key=SecretStr(encryption_key),
    )
    return TOTPHandler(config)


@pytest.fixture(name="custom_totp_handler")
def create_custom_totp_handler() -> TOTPHandler:
    """Create a non-default TOTP handler."""
    encryption_key = TOTPHandler.random_encryption_key()
    config = TOTPConfig(
        totp_issuer="Custom Issuer",
        totp_algorithm=TOTPAlgorithm.SHA512,
        totp_digits=8,
        totp_interval=20,
        totp_tolerance=0,
        totp_attempts_per_code=1,
        totp_max_failed_attempts=7,
        totp_secret_size=64,
        totp_encryption_key=SecretStr(encryption_key),
    )
    return TOTPHandler(config)


def generate_invalid_codes(
    totp_handler: TOTPHandler,
    token: TOTPToken,
    for_time: UTCDatetime,
    num: int = 1,
) -> list[str]:
    """Generate TOTP codes that are invalid during the whole tolerance interval."""
    generate_code = totp_handler.generate_code
    valid_codes = {generate_code(token, for_time, offset) for offset in range(-1, 2)}
    invalid_codes = []
    for _ in range(10_000):
        code = f"{randint(0, 999_999):06d}"
        if code not in valid_codes:
            invalid_codes.append(code)
            if len(invalid_codes) >= num:
                return invalid_codes
    raise RuntimeError("Could not find an invalid TOTP code")


def test_random_encryption_keys():
    """Test that encryption keys can be randomly generated."""
    key = TOTPHandler.random_encryption_key()
    assert isinstance(key, str)
    decoded = base64.b64decode(key)
    assert len(decoded) == 32


def test_default_parameters(totp_handler: TOTPHandler):
    """Check that the default TOTP handler has the expected parameters."""
    assert totp_handler.issuer == "Test Issuer"
    assert str(totp_handler.image) == "https://www.test.dev/logo.png"
    assert totp_handler.digest is hashlib.sha1
    assert totp_handler.digits == 6
    assert totp_handler.interval == 30
    assert totp_handler.tolerance == 1
    assert totp_handler.max_counter_attempts == 3
    assert totp_handler.max_total_attempts == 10
    assert totp_handler.secret_size == 32


def test_generate_token(totp_handler: TOTPHandler):
    """Test generating a TOTP token."""
    token = totp_handler.generate_token()
    decoded_secret = base64.b64decode(token.encrypted_secret)
    assert len(decoded_secret) == 72
    assert token.last_counter == -1
    assert token.counter_attempts == -1


def test_get_secret(totp_handler: TOTPHandler):
    """Test generating a TOTP token."""
    token = totp_handler.generate_token()
    secret = totp_handler.get_secret(token)
    assert isinstance(secret, str)
    assert len(secret) == 32
    assert secret.isalnum()


def test_get_provisioning_uri(totp_handler: TOTPHandler):
    """Test generating a TOTP provisioning URI."""
    token = totp_handler.generate_token()
    secret = totp_handler.get_secret(token)
    uri = totp_handler.get_provisioning_uri(token, name="John Doe")
    assert isinstance(uri, str)
    assert (
        uri == f"otpauth://totp/Test%20Issuer:John%20Doe?secret={secret}"
        "&issuer=Test%20Issuer&image=https%3A%2F%2Fwww.test.dev%2Flogo.png"
    )


def test_generate_code(totp_handler: TOTPHandler):
    """Test generating a TOTP code."""
    token = totp_handler.generate_token()
    code = totp_handler.generate_code(token)
    assert isinstance(code, str)
    assert len(code) == 6
    assert isinstance(int(code), int)


def test_verify_code_with_valid_code(totp_handler: TOTPHandler):
    """Test verification of a valid TOTP code."""
    token = totp_handler.generate_token()
    for_time = now_as_utc()
    code = totp_handler.generate_code(token, for_time)
    assert totp_handler.verify_code(token, code, for_time) is True


def test_token_object_is_modified(totp_handler: TOTPHandler):
    """Test modification of token object after verification."""
    token = totp_handler.generate_token()
    secret = token.encrypted_secret
    assert token.counter_attempts == -1
    assert token.last_counter == -1
    token.counter_attempts = 1
    token.last_counter = 0
    for_time = now_as_utc()
    verified = totp_handler.verify_code(token, "123456", for_time)
    assert token.encrypted_secret == secret
    expected_attempts = -1 if verified else 1
    assert token.counter_attempts == expected_attempts
    assert token.last_counter > 0


def test_verify_code_with_slightly_invalid_code(totp_handler: TOTPHandler):
    """Test verification of a slightly invalid TOTP code."""
    token = totp_handler.generate_token()
    for_time = now_as_utc()
    code = generate_invalid_codes(totp_handler, token, for_time, 1)[0]
    assert totp_handler.verify_code(token, code, for_time) is False


@pytest.mark.parametrize(
    "code",
    [
        "",
        "123",
        "12345",
        "1234567",
        "123456789",
        "-23456",
        "123?56",
        "12345x",
        "abcdef",
    ],
)
def test_verify_code_with_totally_invalid_code(code: str, totp_handler: TOTPHandler):
    """Test verification of a totally invalid TOTP code."""
    token = totp_handler.generate_token()
    assert token.counter_attempts == -1
    assert token.last_counter == -1
    assert totp_handler.verify_code(token, code) is None
    assert token.counter_attempts == -1
    assert token.last_counter == -1


def test_verification_with_time_in_the_past(totp_handler: TOTPHandler):
    """Test that going back in time during validation is rejected."""
    token = totp_handler.generate_token()
    for_time = now_as_utc()
    code = totp_handler.generate_code(token, for_time)
    assert totp_handler.verify_code(token, code, for_time) is True
    for_time -= timedelta(seconds=totp_handler.interval * 3)
    code = totp_handler.generate_code(token, for_time)
    assert totp_handler.verify_code(token, code, for_time) is None


def test_verification_with_time_in_the_future(totp_handler: TOTPHandler):
    """Test that going forward in time during validation is allowed."""
    token = totp_handler.generate_token()
    for_time = now_as_utc()
    code = totp_handler.generate_code(token, for_time)
    assert totp_handler.verify_code(token, code, for_time) is True
    for_time += timedelta(seconds=totp_handler.interval * 3)
    code = totp_handler.generate_code(token, for_time)
    assert totp_handler.verify_code(token, code, for_time) is True


def test_replay_attack(totp_handler: TOTPHandler):
    """Test that replay attacks are rejected."""
    token = totp_handler.generate_token()
    for_time = now_as_utc()
    code = totp_handler.generate_code(token, for_time)
    assert totp_handler.verify_code(token, code, for_time) is True
    assert totp_handler.verify_code(token, code, for_time) is None


def test_rate_limiting_attack(totp_handler: TOTPHandler):
    """Test that too many attempts for one counter are rejected."""
    for_time = now_as_utc()
    token = totp_handler.generate_token()
    invalid_codes = generate_invalid_codes(
        totp_handler, token, for_time, totp_handler.max_counter_attempts
    )
    for code in invalid_codes:
        assert not totp_handler.is_invalid(token)
        assert totp_handler.verify_code(token, code, for_time) is False

    assert not totp_handler.is_invalid(token)
    code = totp_handler.generate_code(token, for_time)
    assert totp_handler.verify_code(token, code, for_time) is None


def test_brute_force_attack(totp_handler: TOTPHandler):
    """Test that too many failed attempts in a row are rejected."""
    for_time = now_as_utc()
    token = totp_handler.generate_token()
    invalid_codes = generate_invalid_codes(
        totp_handler, token, for_time, totp_handler.max_total_attempts
    )
    for code in invalid_codes:
        assert not totp_handler.is_invalid(token)
        assert totp_handler.verify_code(token, code, for_time) is False
        token.counter_attempts = 0  # reset the counter for the current interval

    assert totp_handler.is_invalid(token)
    code = totp_handler.generate_code(token, for_time)
    assert totp_handler.verify_code(token, code, for_time) is None


def test_verification_inside_tolerance_interval(totp_handler: TOTPHandler):
    """Test verification of a valid code inside the tolerance interval."""
    tolerance = totp_handler.tolerance
    for_time = now_as_utc()
    for offset in range(-tolerance, tolerance + 1):
        token = totp_handler.generate_token()
        code = totp_handler.generate_code(token, for_time, offset)
        assert totp_handler.verify_code(token, code, for_time) is True


def test_verification_outside_tolerance_interval(totp_handler: TOTPHandler):
    """Test verification of a valid code outside the tolerance interval."""
    tolerance = totp_handler.tolerance
    for_time = now_as_utc()
    # test both before and after the tolerance interval
    for direction in (-1, 1):
        token = totp_handler.generate_token()
        # determine valid codes inside the tolerance interval
        codes_inside = {
            totp_handler.generate_code(token, for_time, offset)
            for offset in range(-tolerance, tolerance + 1)
        }
        # determine valid codes outside the tolerance interval
        codes_outside = {
            totp_handler.generate_code(token, for_time, offset * direction)
            for offset in range(tolerance + 1, tolerance + 12)
        }
        codes = codes_outside - codes_inside
        assert codes
        code = next(iter(codes))
        assert totp_handler.verify_code(token, code, for_time) is False


def test_custom_parameters(custom_totp_handler: TOTPHandler):
    """Check that the custom TOTP handler has the expected parameters."""
    handler = custom_totp_handler
    assert handler.issuer == "Custom Issuer"
    assert handler.image is None
    assert handler.digest is hashlib.sha512
    assert handler.digits == 8
    assert handler.interval == 20
    assert handler.tolerance == 0
    assert handler.max_counter_attempts == 1
    assert handler.max_total_attempts == 7
    assert handler.secret_size == 64


def test_get_custom_secret(custom_totp_handler: TOTPHandler):
    """Test generating a custom TOTP token."""
    token = custom_totp_handler.generate_token()
    secret = custom_totp_handler.get_secret(token)
    assert isinstance(secret, str)
    assert len(secret) == 64
    assert secret.isalnum()


def test_get_custom_provisioning_uri(custom_totp_handler: TOTPHandler):
    """Test generating a custom TOTP provisioning URI."""
    handler = custom_totp_handler
    token = handler.generate_token()
    secret = handler.get_secret(token)
    uri = handler.get_provisioning_uri(token, name="Dr. Jane Roe")
    assert isinstance(uri, str)
    assert (
        uri == f"otpauth://totp/Custom%20Issuer:Dr.%20Jane%20Roe?secret={secret}"
        "&issuer=Custom%20Issuer&algorithm=SHA512&digits=8&period=20"
    )


def test_verify_with_custom_handler(custom_totp_handler: TOTPHandler):
    """Test verification of a valid TOTP code using a custom handler."""
    token = custom_totp_handler.generate_token()
    for_time = now_as_utc()
    code = custom_totp_handler.generate_code(token, for_time)
    assert len(code) == 8
    assert custom_totp_handler.verify_code(token, code, for_time) is True
    assert custom_totp_handler.verify_code(token, code, for_time) is None
