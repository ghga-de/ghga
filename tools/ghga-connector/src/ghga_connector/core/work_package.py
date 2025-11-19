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
"""This file contains all api calls related to obtaining work package and work order tokens"""

import base64
import json
from collections.abc import Callable
from typing import Any, Literal
from uuid import UUID

import httpx
from ghga_service_commons.utils import crypt
from ghga_service_commons.utils.crypt import decrypt
from pydantic import UUID4, SecretBytes
from tenacity import RetryError

from ghga_connector.config import get_work_package_api_url
from ghga_connector.constants import CACHE_MIN_FRESH
from ghga_connector.core.api_calls.utils import modify_headers_for_cache_refresh
from ghga_connector.core.utils import get_work_package_token

from .. import exceptions

WorkType = Literal["create", "upload", "close", "delete"]


class WorkPackageClient:
    """A client handling calls to the Work Package API and related logic"""

    def __init__(
        self,
        client: httpx.AsyncClient,
        my_private_key: SecretBytes,
        my_public_key: bytes,
    ) -> None:
        """Set up WorkPackageClient and get work package info using private key"""
        self.work_package_api_url = get_work_package_api_url()
        self.client = client
        self.my_private_key = my_private_key
        self.my_public_key = my_public_key

        # Get work package information using user's private key
        package_id, encrypted_token = get_work_package_token(max_tries=3)
        self.package_id = UUID(package_id)
        self.access_token = crypt.decrypt(
            data=encrypted_token, key=my_private_key.get_secret_value()
        )

    async def _call_url(
        self,
        *,
        fn: Callable,
        headers: httpx.Headers,
        url: str,
        body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Call url with provided headers and client method passed as callable."""
        try:
            args = {  # we don't always want to supply 'json' kwarg, so do it like this
                "url": url,
                "headers": headers,
            }
            if body is not None:
                args["json"] = body
            response: httpx.Response = await fn(**args)
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

    async def _get_work_package(self) -> dict[str, Any]:
        """Call Work Package API and retrieve work package information.

        Returns the work package details as a dictionary.

        Raises:
            NoWorkPackageAccessError: If a 403 is received.
            InvalidWorkPackageResponseError: If any other non-200 error code is received.
        """
        url = f"{self.work_package_api_url}/work-packages/{self.package_id}"

        # send authorization header as bearer token
        headers = httpx.Headers({"Authorization": f"Bearer {self.access_token}"})
        response = await self._call_url(fn=self.client.get, headers=headers, url=url)

        status_code = response.status_code

        if status_code == 200:
            return response.json()

        if status_code == 403:
            raise exceptions.NoWorkPackageAccessError(work_package_id=self.package_id)
        raise exceptions.InvalidWorkPackageResponseError(
            url=url, response_code=status_code
        )

    async def get_package_files(self) -> dict[str, str]:
        """Call Work Package API and retrieve work package information.

        Raises:
            NoWorkPackageAccessError: If a 403 is received.
            InvalidWorkPackageResponseError: If any other non-200 error code is received.
        """
        work_package = await self._get_work_package()
        return work_package["files"]

    async def get_package_box_id(self) -> UUID4:
        """Call Work Package API and retrieve FileUploadBox ID.

        Raises:
            NoWorkPackageAccessError: If a 403 is received.
            InvalidWorkPackageResponseError: If any other non-200 error code is received.
        """
        work_package = await self._get_work_package()
        return UUID(work_package["box_id"])

    async def get_download_wot(self, *, file_id: str, bust_cache: bool = False) -> str:
        """Get a work order token from the Work Package API enabling download of a single file"""
        url = f"{self.work_package_api_url}/work-packages/{self.package_id}/files/{file_id}/work-order-tokens"
        download_wot = await self._get_work_order_token(url=url, bust_cache=bust_cache)
        return download_wot

    async def get_upload_wot(
        self,
        *,
        work_type: WorkType,
        box_id: UUID4,
        file_id: UUID4 | None = None,
        alias: str | None = None,
        bust_cache: bool = False,
    ) -> str:
        """Get a work order token from the Work Package API enabling file upload operations for
        a single file.
        """
        url = f"{self.work_package_api_url}/work-packages/{self.package_id}/boxes/{box_id}/work-order-tokens"
        body = {
            "work_type": work_type,
            "alias": alias,
            "file_id": str(file_id),
        }
        upload_wot = await self._get_work_order_token(
            url=url, bust_cache=bust_cache, body=body
        )
        return upload_wot

    async def _get_work_order_token(
        self, *, url: str, bust_cache: bool, body: dict[str, Any] | None = None
    ) -> str:
        """Call Work Package API endpoint to retrieve and decrypt work order token.

        Raises:
            NoWorkPackageAccessError: If the Work Package API returns an unauthorized response.
            InvalidWorkPackageResponseError: If the Work Package API returns an response
                code other than 403 or 201, OR the response doesn't contain a WOT.
        """
        # send authorization header as bearer token
        headers = httpx.Headers(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Cache-Control": f"min-fresh={CACHE_MIN_FRESH}",
            }
        )
        if bust_cache:
            modify_headers_for_cache_refresh(headers)

        response = await self._call_url(
            fn=self.client.post, body=body, headers=headers, url=url
        )

        status_code = response.status_code
        if status_code != 201:
            if status_code == 403:
                raise exceptions.NoWorkPackageAccessError(
                    work_package_id=self.package_id
                )
            raise exceptions.InvalidWorkPackageResponseError(
                url=url, response_code=status_code
            )

        encrypted_token = response.json()
        if not encrypted_token or not isinstance(encrypted_token, str):
            raise exceptions.InvalidWorkPackageResponseError(
                url=url, response_code=status_code
            )
        decrypted_token = _decrypt(data=encrypted_token, key=self.my_private_key)
        self._check_public_key(decrypted_token)
        return decrypted_token

    def _check_public_key(self, token: str):
        """Check that the public key inside the token matches the expectation.

        If the public key cannot be retrieved from the token, ignore this error,
        an authorization error will then be raised later in the process.

        Raises:
            PubKeyMismatchError: if the public key does not match.
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

    async def make_auth_headers(self, decrypted_token: str) -> httpx.Headers:
        """
        Prepare headers for calling Upload or Download API with a decrypted work order
        token.

        The calls will use the cache if possible while the cached responses are still
        fresh for at least another `CACHE_MIN_FRESH` seconds.
        """
        # build headers
        headers = httpx.Headers(
            {
                "Accept": "application/json",
                "Authorization": f"Bearer {decrypted_token}",
                "Content-Type": "application/json",
                "Cache-Control": f"min-fresh={CACHE_MIN_FRESH}",
            }
        )

        return headers


def _decrypt(*, data: str, key: SecretBytes):
    """Factored out decryption so this can be mocked."""
    return decrypt(data=data, key=key.get_secret_value())
