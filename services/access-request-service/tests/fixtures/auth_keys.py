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

"""Generate signing keys for testing"""

from ghga_service_commons.utils.jwt_helpers import (
    generate_jwk,
    sign_and_serialize_token,
)

AUTH_CLAIMS_STEWARD = {
    "name": "Rod Steward",
    "email": "steward@ghga.de",
    "id": "id-of-rod-steward@ghga.de",
    "roles": ["data_steward@ghga.de"],
}

AUTH_KEY_PAIR = generate_jwk()

ARS_AUTH_KEY = AUTH_KEY_PAIR.export(private_key=False)

TOKEN = sign_and_serialize_token(AUTH_CLAIMS_STEWARD, AUTH_KEY_PAIR)


def print_auth_key_env() -> None:
    """Print environment setting for the auth key."""
    print(f"{ARS_AUTH_KEY=!r}")
    print("echo Bearer token:", TOKEN)


if __name__ == "__main__":
    print_auth_key_env()
