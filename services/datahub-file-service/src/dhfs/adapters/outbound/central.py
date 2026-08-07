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

"""Client class for communicating with the GHGA Central API"""

import base64
import logging
from json import JSONDecodeError

import httpx
from jwcrypto.jwk import JWK
from pydantic import Field, HttpUrl, SecretStr, ValidationError
from pydantic_settings import BaseSettings
from tenacity import RetryError

from dhfs.adapters.outbound.http import check_for_request_errors
from dhfs.constants import AUTH_TOKEN_VALID_SECONDS, JWT_AUD, JWT_ISS
from dhfs.core import models
from dhfs.ports.outbound.central import CentralClientPort
from ghga_service_commons.utils.crypt import encrypt
from ghga_service_commons.utils.jwt_helpers import sign_and_serialize_token

log = logging.getLogger(__name__)


class CentralClientConfig(BaseSettings):
    """Configuration required for the CentralClient class"""

    central_api_crypt4gh_public_key: str = Field(
        default=...,
        description="The Crypt4GH public key used by the Central API. This is used to"
        + " encrypt new file encryption secrets.",
    )
    central_api_url: HttpUrl = Field(
        default=...,
        description="The base URL used to connect to to the GHGA Central API",
    )
    data_hub_signing_key: SecretStr = Field(
        default=...,
        description="The Data Hub's private JWK for signing JWT auth tokens",
        examples=['{"crv": "P-256", "kty": "EC", "x": "...", "y": "...", "d": "..."}'],
    )
    storage_alias: str = Field(
        default=...,
        description=(
            "An alias identifying the Data Hub at which this instance of DHFS is"
            + " running. This value should be set in coordination with GHGA Central."
        ),
        examples=["HD01", "TUE01", "B01"],
    )


class CentralClient(CentralClientPort):
    """This class communicates with GHGA Central to learn about new file uploads"""

    def __init__(
        self,
        *,
        config: CentralClientConfig,
        httpx_client: httpx.AsyncClient,
    ) -> None:
        """Initialize the CentralClient instance"""
        self._httpx_client = httpx_client
        self._storage_alias = config.storage_alias
        self._central_public_key = config.central_api_crypt4gh_public_key
        self._base_url = str(config.central_api_url).rstrip("/")
        self._signing_key = JWK.from_json(
            config.data_hub_signing_key.get_secret_value()
        )
        if not self._signing_key.has_private:
            value_error = ValueError("No private token-signing key found.")
            log.error(value_error)
            raise value_error

    def _make_jwt(self) -> str:
        claims: dict[str, str] = {
            "iss": JWT_ISS,
            "aud": JWT_AUD,
            "sub": self._storage_alias,
        }
        return sign_and_serialize_token(
            claims=claims, key=self._signing_key, valid_seconds=AUTH_TOKEN_VALID_SECONDS
        )

    def _auth_headers(self) -> dict[str, str]:
        """Create an authorization header with a bearer token containing a fresh JWT"""
        return {"Authorization": f"Bearer {self._make_jwt()}"}

    def _response_to_object_id_list(self, response: httpx.Response) -> list[str]:
        """Returns a list of strings from an httpx Response.

        Raises:
        - ResponseFormatError if response body parsing fails.
        """
        try:
            body = response.json()
            if not (
                isinstance(body, list) and all(isinstance(value, str) for value in body)
            ):
                raise TypeError("Response did not contain a list of strings")
        except (JSONDecodeError, TypeError) as err:
            raise self.ResponseFormatError(str(response.url)) from err
        return body

    def _response_to_file_upload_list(
        self, response: httpx.Response
    ) -> list[models.FileUpload]:
        """Extract a list of FileUploads from an httpx Response.

        Raises:
        - ResponseFormatError if response body parsing fails.
        """
        try:
            body = response.json()
            return list(map(models.FileUpload.model_validate, body))
        except (JSONDecodeError, ValidationError, TypeError) as err:
            raise self.ResponseFormatError(str(response.url)) from err

    async def fetch_new_uploads(self) -> list[models.FileUpload]:
        """Fetch a list of files that need to be interrogated and re-encrypted.

        Raises:
        - CentralAPIError if the request to the central API fails.
        - UpgradeRequiredError if the central API indicates this DHFS instance is outdated
        - ResponseFormatError if response body parsing fails.
        """
        url = f"{self._base_url}/storages/{self._storage_alias}/uploads"
        log.debug("Fetching new uploads from %s.", url)
        try:
            response = await self._httpx_client.get(
                url=url, headers=self._auth_headers()
            )
        except RetryError as retry_error:
            check_for_request_errors(retry_error, url)
            response = retry_error.last_attempt.result()

        if (status_code := response.status_code) != 200:
            if status_code == 426:
                raise self.UpgradeRequiredError()
            raise self.CentralAPIError(url=url, status_code=status_code)

        return self._response_to_file_upload_list(response)

    async def get_removable_files(self, *, object_ids: list[str]) -> list[str]:
        """Ask the GHGA Central API if the objects corresponding to the given object IDs
        can be removed from `interrogation` bucket.

        Returns a list of object IDs that may be removed from the bucket.

        Raises:
        - CentralAPIError if the request to the central API fails.
        - UpgradeRequiredError if the central API indicates this DHFS instance is outdated
        """
        url = f"{self._base_url}/storages/{self._storage_alias}/uploads/can_remove"
        log.debug(
            "Querying GHGA Central API about removability of %i files (URL is %s).",
            len(object_ids),
            url,
        )
        try:
            response = await self._httpx_client.post(
                url=url, json=object_ids, headers=self._auth_headers()
            )
        except RetryError as retry_error:
            check_for_request_errors(retry_error, url)
            response = retry_error.last_attempt.result()

        if (status_code := response.status_code) != 200:
            if status_code == 426:
                raise self.UpgradeRequiredError()
            raise self.CentralAPIError(url=url, status_code=status_code)

        removable = self._response_to_object_id_list(response)
        log.debug("Central API indicated %i file(s) can be removed.", len(removable))
        return removable

    async def submit_interrogation_report(
        self, *, report: models.InterrogationReport
    ) -> None:
        """Submit a file interrogation report to GHGA Central

        Raises:
        - CentralAPIError if the request to the central API fails.
        - UpgradeRequiredError if the central API indicates this DHFS instance is outdated
        """
        body = report.model_dump(mode="json")
        url = f"{self._base_url}/storages/{self._storage_alias}/interrogation-reports"
        msg = (
            "was successfully re-encrypted"
            if report.passed
            else "could not be re-encrypted"
        )
        log.debug(
            "File %s: Informing GHGA Central that the file %s.",
            report.file_id,
            msg,
            extra={"file_id": report.file_id, "passed": report.passed, "url": url},
        )

        # Encrypt secret (core class doesn't know central api public key)
        if report.secret:
            secret = report.secret.get_secret_value()
            encoded_secret = base64.urlsafe_b64encode(secret).decode("utf-8")
            body["secret"] = encrypt(encoded_secret, key=self._central_public_key)

        try:
            response = await self._httpx_client.post(
                url=url, headers=self._auth_headers(), json=body
            )
        except RetryError as retry_error:
            check_for_request_errors(retry_error, url)
            response = retry_error.last_attempt.result()

        if (status_code := response.status_code) != 201:
            if status_code == 426:
                raise self.UpgradeRequiredError()
            raise self.CentralAPIError(url=url, status_code=status_code)

        log.info(
            "File %s: Submitted report to GHGA Central indicating that the file %s.",
            report.file_id,
            msg,
        )
