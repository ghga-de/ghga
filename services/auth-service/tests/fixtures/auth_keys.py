#!/usr/bin/env python3

# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Generate signing keys for testing"""

from importlib import reload
from os import environ
from typing import Any

from jwcrypto import jwk

from auth_service.config import CONFIG

auth_adapter = "auth_adapter" in CONFIG.provide_apis


def generate_jwk() -> jwk.JWK:
    """Generate a random EC based JWK."""
    return jwk.JWK.generate(kty="EC", crv="P-256")


def generate_jwk_set() -> jwk.JWKSet:
    """Generate a key set with one test key."""
    jwk_set = jwk.JWKSet()
    test_jwk = generate_jwk()
    test_jwk["kid"] = "test"
    jwk_set.add(test_jwk)
    return jwk_set


def set_auth_keys_env() -> None:
    """Set signing keys as environment variables."""
    for key, value in generate_keys().items():
        if value is None:
            if key in environ:
                del environ[key]
        else:
            environ[key] = value


def generate_keys() -> dict[str, Any]:
    """Generate dictionary with signing keys."""
    auth_adapter = "ext_auth" in environ.get(
        "AUTH_SERVICE_PROVIDE_APIS", environ.get("auth_service_provide_apis", "")
    )
    int_key = generate_jwk().export
    env: dict[str, Any] = {
        "AUTH_SERVICE_AUTH_KEY": int_key(private_key=auth_adapter),
        "TEST_AUTH_SERVICE_AUTH_KEY": int_key(private_key=True),
    }
    if auth_adapter:
        ext_keys = generate_jwk_set().export
        env.update(
            {
                "AUTH_SERVICE_AUTH_EXT_KEYS": ext_keys(private_keys=False),
                "TEST_AUTH_SERVICE_AUTH_EXT_KEYS": ext_keys(private_keys=True),
            }
        )
    else:
        env.update(
            {
                "AUTH_SERVICE_AUTH_EXT_KEYS": None,
                "TEST_AUTH_SERVICE_AUTH_EXT_KEYS": None,
            }
        )
    return env


def print_auth_keys_env() -> None:
    """Print environment for signing keys."""
    for key, value in generate_keys().items():
        if value is None:
            print(f"unset {key}")
        else:
            print(f"{key}={value!r}")


def reload_auth_key_config(auth_adapter: bool = auth_adapter) -> None:
    """Reload the configuration for the signing keys."""
    environ["AUTH_SERVICE_PROVIDE_APIS"] = '["ext_auth"]' if auth_adapter else "[]"
    set_auth_keys_env()

    from auth_service import config

    reload(config)

    if auth_adapter:
        from auth_service.auth_adapter.core import auth
    else:
        from auth_service.user_management.rest import auth  # type: ignore[no-redef]

    reload(auth)

    from . import utils

    reload(utils)


if __name__ == "__main__":
    print_auth_keys_env()
