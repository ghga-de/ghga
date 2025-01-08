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
"""This file contains all api calls related to obtaining work package and work order tokens"""

import base64
import json
from collections.abc import Callable

import httpx
from ghga_service_commons.utils.crypt import decrypt
from tenacity import RetryError

from ghga_connector.constants import CACHE_MIN_FRESH

from . import exceptions, retry_handler


class WorkPackageAccessor:
    """Wrapper for WPS associated API call parameters"""

    def __init__(  # noqa: PLR0913
        self,
        access_token: str,
        api_url: str,
        client: httpx.AsyncClient,
        dcs_api_url: str,
        package_id: str,
        my_private_key: bytes,
        my_public_key: bytes,
    ) -> None:
        self.access_token = access_token
        self.api_url = api_url
        self.client = client
        self.dcs_api_url = dcs_api_url
        self.package_id = package_id
        self.my_private_key = my_private_key
        self.my_public_key = my_public_key

    async def _call_url(
        self, *, fn: Callable, headers: httpx.Headers, url: str
    ) -> httpx.Response:
        """Call url with provided headers and client method passed as callable."""
        try:
            response: httpx.Response = await retry_handler(
                fn=fn,
                headers=headers,
                url=url,
            )
        except RetryError as retry_error:
            wrapped_exception = retry_error.last_attempt.exception()

            if isinstance(wrapped_exception, httpx.RequestError):
                raise exceptions.RequestFailedError(url=url) from retry_error
            elif wrapped_exception:
                raise wrapped_exception from retry_error
            elif result := retry_error.last_attempt.result():
                response = result
            else:
                raise

        return response

    async def get_package_files(self) -> dict[str, str]:
        """Call WPS endpoint and retrieve work package information."""
        url = f"{self.api_url}/work-packages/{self.package_id}"

        # send authorization header as bearer token
        headers = httpx.Headers({"Authorization": f"Bearer {self.access_token}"})
        response = await self._call_url(fn=self.client.get, headers=headers, url=url)

        status_code = response.status_code
        if status_code != 200:
            if status_code == 403:
                raise exceptions.NoWorkPackageAccessError(
                    work_package_id=self.package_id
                )
            raise exceptions.InvalidWPSResponseError(url=url, response_code=status_code)

        work_package = response.json()
        return work_package["files"]

    async def get_work_order_token(self, *, file_id: str) -> str:
        """Call WPS endpoint to retrieve and decrypt work order token."""
        url = f"{self.api_url}/work-packages/{self.package_id}/files/{file_id}/work-order-tokens"

        # send authorization header as bearer token
        headers = httpx.Headers(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Cache-Control": f"min-fresh={CACHE_MIN_FRESH}",
            }
        )
        response = await self._call_url(fn=self.client.post, headers=headers, url=url)

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
            ).decode("ascii")
        except Exception:
            mismatch = False
        if mismatch:
            raise exceptions.PubKeyMismatchError()


def _decrypt(*, data: str, key: bytes):
    """Factored out decryption so this can be mocked."""
    return decrypt(data=data, key=key)
