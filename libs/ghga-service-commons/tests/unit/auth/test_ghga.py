# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test the auth.ghga module."""


from ghga_service_commons.auth.ghga import (
    AcademicTitle,
    AuthConfig,
    AuthContext,
    UserStatus,
    has_role,
    is_active,
)
from ghga_service_commons.utils.jwt_helpers import generate_jwk
from ghga_service_commons.utils.utc_dates import utc_datetime

context_kwargs = {
    "name": "John Doe",
    "email": "john@home.org",
    "title": AcademicTitle.DR,
    "iat": utc_datetime(2022, 11, 15, 12, 0, 0),
    "exp": utc_datetime(2022, 11, 15, 13, 0, 0),
    "id": "some-internal-id",
    "ext_id": "some-external-id",
    "role": "admin",
    "status": UserStatus.ACTIVE,
}


def test_create_auth_context():
    """Test that a GHGA auth context can be crated."""
    context = AuthContext(**context_kwargs)  # type: ignore
    assert context.model_dump() == context.model_dump()


def test_has_role():
    """Test that roles of the GHGA auth context can be checked."""
    context = AuthContext(**context_kwargs)  # type: ignore
    assert context.role == "admin"
    assert has_role(context, "admin")
    assert not has_role(context, "operator")
    assert not has_role(context, "admin@home")
    assert not has_role(context, "admin@office")
    context.role = "admin@office"
    assert has_role(context, "admin")
    assert not has_role(context, "operator")
    assert has_role(context, "admin@office")
    assert not has_role(context, "admin@home")
    context.status = UserStatus.INACTIVE
    assert not has_role(context, "admin")
    assert not has_role(context, "admin@office")
    context.status = UserStatus.INVALID
    assert not has_role(context, "admin")
    assert not has_role(context, "admin@office")


def test_is_active():
    """Test that the active state of the GHGA auth context can be checked."""
    context = AuthContext(**context_kwargs)  # type: ignore
    assert is_active(context)
    context.status = UserStatus.INACTIVE
    assert not is_active(context)
    context.status = UserStatus.INVALID
    assert not is_active(context)


def test_create_auth_config():
    """Test that a GHGA auth config can be crated."""
    auth_key = generate_jwk().export(private_key=False)
    config = AuthConfig(auth_key=auth_key)  # type: ignore
    assert config.auth_algs == ["ES256"]
    assert config.auth_check_claims == {
        "name": None,
        "email": None,
        "iat": None,
        "exp": None,
    }
    assert config.auth_map_claims == {}
