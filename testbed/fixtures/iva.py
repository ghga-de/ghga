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

"""Fixture for Independent Verification Addresses"""

from collections.abc import Generator
from dataclasses import dataclass

from httpx import Response
from pydantic import BaseModel
from pytest import fixture

from .config import Config
from .http_client import HttpClient

__all__ = ["iva_fixture", "IVAFixture"]


class IVA(BaseModel):
    id: str
    type: str
    value: str


@dataclass
class IVAFixture:
    """Fixture for Independent Verification Addresses"""

    config: Config
    http: HttpClient

    def create(self, iva_type: str, iva_value: str, user_id: str, headers: dict) -> IVA:
        """Create a new IVA for the given user"""
        data = {"type": iva_type, "value": iva_value}
        url = f"{self.config.ums_url}/users/{user_id}/ivas"
        response = self.http.post(url, json=data, headers=headers)
        assert response.status_code == 201, f"Failed to create IVA: {response.text}"
        return IVA(type=iva_type, value=iva_value, **response.json())

    def retrieve(self, user_id: str, headers: dict) -> list:
        """Retrieve the list of user IVAs"""
        url = f"{self.config.ums_url}/users/{user_id}/ivas"
        response = self.http.get(url, headers=headers)
        assert response.status_code == 200, f"Failed to retrieve IVAs: {response.text}"
        return response.json()

    def delete(self, iva_ids: str | list[str], user_id: str, headers: dict) -> None:
        """Delete the given IVAs for the user"""
        if isinstance(iva_ids, str):
            iva_ids = [iva_ids]
        elif not isinstance(iva_ids, list):
            assert False, "Invalid type for IVA list. Can be either a string or a list."
        for iva_id in iva_ids:
            url = f"{self.config.ums_url}/users/{user_id}/ivas/{iva_id}"
            response = self.http.delete(url, headers=headers)
            assert response.status_code == 204, f"Failed to delete IVA: {response.text}"

    def request_verification(self, iva_id: str, headers: dict) -> Response:
        url = f"{self.config.ums_url}/rpc/ivas/{iva_id}/request-code"
        return self.http.post(url, headers=headers)

    def create_verification(self, iva_id: str, headers: dict) -> Response:
        url = f"{self.config.ums_url}/rpc/ivas/{iva_id}/create-code"
        response = self.http.post(url, headers=headers)
        assert (
            response.status_code == 201
        ), f"Failed to create verification code: {response.text}"
        results = response.json()
        assert "verification_code" in results, f"Verification code not found: {results}"
        return results["verification_code"]

    def confirm_transmission(self, iva_id: str, headers: dict) -> Response:
        url = f"{self.config.ums_url}/rpc/ivas/{iva_id}/code-transmitted"
        return self.http.post(url, headers=headers)

    def validate_code(
        self, verification_code: str, iva_id: str, headers: dict
    ) -> Response:
        url = f"{self.config.ums_url}/rpc/ivas/{iva_id}/validate-code"
        data = {"verification_code": verification_code}
        return self.http.post(url, json=data, headers=headers)


@fixture(name="iva", scope="session")
def iva_fixture(config: Config, http: HttpClient) -> Generator[IVAFixture, None, None]:
    """Pytest fixture for IVA operations"""
    yield IVAFixture(config=config, http=http)
