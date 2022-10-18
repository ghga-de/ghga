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

"""Generate signing keys for testing"""

from os import environ

from jwcrypto import jwk


def generate_jwk() -> jwk.JWK:
    """Generate a random EC based JWK."""
    return jwk.JWK.generate(kty="EC", crv="P-256")


def generate_auth_ext_keys():
    """Create external key set (with private keys)."""
    external_jwks = jwk.JWKSet()
    external_jwk = generate_jwk()
    external_jwk["kid"] = "test"
    external_jwks.add(external_jwk)
    return external_jwks.export(private_keys=True)


def generate_auth_int_keys():
    """Create internal key pair."""
    internal_jwk = generate_jwk()
    return internal_jwk.export(private_key=True)


def generate_keys():
    """Generate dictionary with signing keys."""
    return dict(
        AUTH_SERVICE_AUTH_EXT_KEYS=generate_auth_ext_keys(),
        AUTH_SERVICE_AUTH_INT_KEYS=generate_auth_int_keys(),
    )


def set_auth_keys_env():
    """Set signing keys as environment variables."""
    for key, value in generate_keys().items():
        environ[key] = value


def print_auth_keys_env():
    """Print environment for signing keys."""
    for key, value in generate_keys().items():
        print(f"{key}={value!r}")


if __name__ == "__main__":
    print_auth_keys_env()
