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

BASE_DIR = Path(__file__).parent.resolve()

TOKEN_LIFESPAN = 30  # seconds
TEST_DS_ID = UUID("f698158d-8417-4368-bb45-349277bc45ee")
TEST_BOX_ID = UUID("bf344cd4-0c1b-434a-93d1-36a11b6b02d9")
INVALID_HEADER: dict[str, str] = {"Authorization": "Bearer ab12"}

DS_AUTH_CLAIMS = {
    "name": "John Doe",
    "email": "john@home.org",
    "title": "Dr.",
    "id": str(TEST_DS_ID),
    "roles": ["data_steward"],
}
USER_AUTH_CLAIMS = DS_AUTH_CLAIMS.copy()
del USER_AUTH_CLAIMS["roles"]


def headers_for_token(token: str) -> dict[str, str]:
    """Get the Authorization headers for the given token."""
    return {"Authorization": f"Bearer {token}"}
