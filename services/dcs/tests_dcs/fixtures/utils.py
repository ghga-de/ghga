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

"""General testing utilities"""

from pathlib import Path
from typing import TypeAlias

from ghga_service_commons.utils import jwt_helpers
from ghga_service_commons.utils.crypt import encode_key, generate_key_pair
from jwcrypto.jwk import JWK

from dcs.core import auth_policies

BASE_DIR = Path(__file__).parent.resolve()


SignedToken: TypeAlias = str


def generate_work_order_token(
    *,
    file_id: str,
    jwk: JWK,
    valid_seconds: int = 30,
) -> SignedToken:
    """Generate work order token for testing"""
    # we don't need the actual user pubkey
    user_pubkey = encode_key(generate_key_pair().public)
    # generate minimal test token
    wot = auth_policies.WorkOrderContext(
        type="download",
        file_id=file_id,
        user_id="007",
        user_public_crypt4gh_key=user_pubkey,
        full_user_name="John Doe",
        email="john.doe@test.com",
    )
    claims = wot.model_dump()

    signed_token = jwt_helpers.sign_and_serialize_token(
        claims=claims, key=jwk, valid_seconds=valid_seconds
    )
    return signed_token


def generate_token_signing_keys() -> JWK:
    """Generate JWK credentials that can be used for signing and verification
    of JWT tokens.
    """
    return jwt_helpers.generate_jwk()
