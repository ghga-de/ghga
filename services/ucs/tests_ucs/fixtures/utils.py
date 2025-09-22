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

"""General testing utilities"""

from pathlib import Path
from typing import Literal, TypeAlias
from uuid import UUID, uuid4

from ghga_service_commons.utils import jwt_helpers
from jwcrypto.jwk import JWK
from pydantic import UUID4

from ucs.adapters.inbound.fastapi_ import rest_models as models

BASE_DIR = Path(__file__).parent.resolve()

TOKEN_LIFESPAN = 30  # seconds

SignedToken: TypeAlias = str


def _make_auth_header(work_order, jwk) -> dict[str, str]:
    """Make an auth header from the supplied work order"""
    claims = work_order.model_dump(mode="json")
    signed_token = jwt_helpers.sign_and_serialize_token(
        claims=claims, key=jwk, valid_seconds=TOKEN_LIFESPAN
    )
    return {"Authorization": f"Bearer {signed_token}"}


def create_file_box_token_header(*, jwk: JWK) -> dict[str, str]:
    """Generate CreateFileBoxWorkOrder token for testing."""
    work_order = models.CreateFileBoxWorkOrder(work_type="create")
    return _make_auth_header(work_order, jwk)


def change_file_box_token_header(
    *,
    box_id: UUID = uuid4(),
    work_type: Literal["lock", "unlock"] = "lock",
    jwk: JWK,
) -> dict[str, str]:
    """Generate ChangeFileBoxWorkOrder token for testing.

    Leave box_id unspecified to use a random value.
    """
    work_order = models.ChangeFileBoxWorkOrder(work_type=work_type, box_id=box_id)
    return _make_auth_header(work_order, jwk)


def view_file_box_token_header(*, box_id: UUID = uuid4(), jwk: JWK) -> dict[str, str]:
    """Generate ViewFileBoxWorkOrder token for testing.

    Leave box_id unspecified to use a random value.
    """
    work_order = models.ViewFileBoxWorkOrder(work_type="view", box_id=box_id)
    return _make_auth_header(work_order, jwk)


def create_file_token_header(
    *,
    box_id: UUID = uuid4(),
    alias: str = "junk",
    jwk: JWK,
) -> dict[str, str]:
    """Generate CreateFileWorkOrder token for testing.

    Leave box_id and alias unspecified to use random values.
    Work_type can be specified here to test with wrong work type.
    """
    work_order = models.CreateFileWorkOrder(
        work_type="create", box_id=box_id, alias=alias
    )
    return _make_auth_header(work_order, jwk)


def upload_file_token_header(
    *,
    box_id: UUID = uuid4(),
    file_id: UUID4 = uuid4(),
    jwk: JWK,
) -> dict[str, str]:
    """Generate UploadFileWorkOrder token with type UPLOAD for testing.

    Leave box_id and file_id unspecified to use random values.
    """
    work_order = models.UploadFileWorkOrder(
        work_type="upload", box_id=box_id, file_id=file_id
    )
    return _make_auth_header(work_order, jwk)


def close_file_token_header(
    *,
    box_id: UUID = uuid4(),
    file_id: UUID4 = uuid4(),
    jwk: JWK,
) -> dict[str, str]:
    """Generate CloseFileWorkOrder token for testing.

    Leave box_id and file_id unspecified to use random values.
    """
    work_order = models.CloseFileWorkOrder(
        work_type="close", box_id=box_id, file_id=file_id
    )
    return _make_auth_header(work_order, jwk)


def delete_file_token_header(
    *,
    box_id: UUID = uuid4(),
    file_id: UUID4 = uuid4(),
    jwk: JWK,
) -> dict[str, str]:
    """Generate DeleteFileWorkOrder token for testing.

    Leave box_id and file_id unspecified to use random values.
    """
    work_order = models.DeleteFileWorkOrder(
        work_type="delete", box_id=box_id, file_id=file_id
    )
    return _make_auth_header(work_order, jwk)
