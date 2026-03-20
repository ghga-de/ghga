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

"""Utils for Fixture handling."""

from pathlib import Path
from uuid import UUID

from ghga_service_commons.utils import jwt_helpers
from jwcrypto.jwk import JWK
from pydantic import UUID4

from rs.adapters.inbound.fastapi_.rest_models import MapFileIdsWorkOrder

BASE_DIR = Path(__file__).parent.resolve()

TOKEN_LIFESPAN = 30  # seconds
DATA_STEWARD_ID = UUID("6d1a41c3-de07-42f8-80ef-243aa69b6261")


def _make_auth_header(work_order, jwk) -> dict[str, str]:
    """Make an auth header from the supplied work order"""
    claims = work_order.model_dump(mode="json")
    signed_token = jwt_helpers.sign_and_serialize_token(
        claims=claims, key=jwk, valid_seconds=TOKEN_LIFESPAN
    )
    return {"Authorization": f"Bearer {signed_token}"}


def map_file_ids_token_header(
    *, user_id: UUID4 = DATA_STEWARD_ID, uos_jwk: JWK, study_pid: str
) -> dict[str, str]:
    """Generate MapFileIdsWorkOrder token for testing."""
    work_order = MapFileIdsWorkOrder(
        work_type="map", user_id=user_id, study_pid=study_pid
    )
    return _make_auth_header(work_order, uos_jwk)
