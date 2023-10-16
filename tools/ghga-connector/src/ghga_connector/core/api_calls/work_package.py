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
"""This file contains all api calls related to obtaining work package and work order tokens"""

import base64
import json
from dataclasses import dataclass

import httpx
from ghga_service_commons.utils.crypt import decrypt

from ghga_connector.core import exceptions
from ghga_connector.core.client import httpx_client


@dataclass
class WorkPackageAccessor:
    """Wrapper for WPS associated API call parameters"""

    access_token: str
    api_url: str
    dcs_api_url: str
    package_id: str
    my_private_key: bytes
    my_public_key: bytes

    def get_package_files(self) -> dict[str, str]:
        """Call WPS endpoint and retrieve work package information."""
        url = f"{self.api_url}/work-packages/{self.package_id}"

        # send authorization header as bearer token
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            with httpx_client() as client:
                response = client.get(url=url, headers=headers)
        except httpx.RequestError as request_error:
            raise exceptions.RequestFailedError(url=url) from request_error

        status_code = response.status_code
        if status_code != 200:
            if status_code == 403:
                raise exceptions.NoWorkPackageAccessError(
                    work_package_id=self.package_id
                )
            raise exceptions.InvalidWPSResponseError(url=url, response_code=status_code)

        work_package = response.json()
        return work_package["files"]

    def get_work_order_token(self, *, file_id: str) -> str:
        """Call WPS endpoint to retrieve and decrypt work order token."""
        url = f"{self.api_url}/work-packages/{self.package_id}/files/{file_id}/work-order-tokens"

        # send authorization header as bearer token
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            with httpx_client() as client:
                response = client.post(url=url, headers=headers)
        except httpx.RequestError as request_error:
            raise exceptions.RequestFailedError(url=url) from request_error

        status_code = response.status_code
        if status_code != 201:
            if status_code == 403:
                raise exceptions.NoWorkPackageAccessError(
                    work_package_id=self.package_id
                )
            raise exceptions.InvalidWPSResponseError(url=url, response_code=status_code)

        encrypted_token = response.json()
        if not encrypted_token or not isinstance(encrypted_token, str):
            raise exceptions.InvalidWPSResponseError(url=url, response_code=status_code)
        decrypted_token = _decrypt(data=encrypted_token, key=self.my_private_key)
        self._check_public_key(decrypted_token)
        return decrypted_token

    def _check_public_key(self, token: str):
        """Check that the public key inside the token matches the expectation.

        If the public key cannot be retrieved from the token, ignore this error,
        an authorization error will then be raised later in the process.
        """
        try:
            mismatch = json.loads(
                base64.b64decode(token.split(".", 2)[1]).decode("utf-8")
            )["user_public_crypt4gh_key"] != base64.b64encode(
                self.my_public_key
            ).decode(
                "ascii"
            )
        except Exception:  # pylint: disable=broad-exception-caught
            mismatch = False
        if mismatch:
            raise exceptions.PubKeyMismatchError()


def _decrypt(*, data: str, key: bytes):
    """Factored out decryption so this can be mocked."""
    return decrypt(data=data, key=key)
