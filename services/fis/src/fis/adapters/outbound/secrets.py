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

"""SecretsClient implementation"""

import logging

import httpx
import tenacity
from pydantic import Field, HttpUrl, SecretBytes
from pydantic_settings import BaseSettings

from fis.ports.outbound.secrets import SecretsClientPort

log = logging.getLogger(__name__)


class SecretsClientConfig(BaseSettings):
    """Configuration required for interfacing with the Secrets API"""

    ekss_api_url: HttpUrl = Field(
        default=...,
        description="The base URL for the EKSS API",
        examples=["http://127.0.0.1/ekss"],
    )


class SecretsClient(SecretsClientPort):
    """A class that interfaces with the Secrets API"""

    def __init__(self, *, config: SecretsClientConfig, httpx_client: httpx.AsyncClient):
        """Initialize the SecretsClient"""
        self._api_base_url = str(config.ekss_api_url).rstrip("/")
        self._httpx_client = httpx_client

    async def deposit_secret(self, *, secret: SecretBytes) -> str:
        """Deposit an encrypted file encryption secret with the Secrets API

        Returns the secret ID.
        """
        try:
            response = await self._httpx_client.post(
                f"{self._api_base_url}/secrets",
                content=secret.get_secret_value(),  # still encrypted
            )
        except tenacity.RetryError as err:
            exception = err.last_attempt.exception()
            reason = (
                str(exception.args[0]) if exception and exception.args else "Unknown"
            )
            log.error(
                "Failed to deposit secret because of the following reason: %s", reason
            )
            raise self.SecretsApiError() from err
        except httpx.HTTPError as err:
            # Catch any httpx errors that weren't wrapped in RetryError
            reason = str(err.args[0]) if err.args else str(err)
            log.error(
                "Failed to deposit secret because of the following reason: %s", reason
            )
            raise self.SecretsApiError() from err

        if response.status_code != 201:
            log.error(
                "Received status code %i while trying to deposit secret.",
                response.status_code,
            )
            raise self.SecretsApiError()

        return response.json()

    async def delete_secret(self, *, secret_id: str) -> None:
        """Delete a file encryption secret from the Secrets API"""
        try:
            response = await self._httpx_client.delete(
                f"{self._api_base_url}/secrets/{secret_id}",
            )
        except tenacity.RetryError as err:
            exception = err.last_attempt.exception()
            reason = (
                str(exception.args[0]) if exception and exception.args else "Unknown"
            )
            log.error(
                "Failed to delete secret because of the following reason: %s", reason
            )
            raise self.SecretsApiError() from err
        except httpx.HTTPError as err:
            reason = str(err.args[0]) if err.args else str(err)
            log.error(
                "Failed to delete secret because of the following reason: %s", reason
            )
            raise self.SecretsApiError() from err

        if response.status_code not in (204, 404):
            log.error(
                "Received status code %i while trying to delete secret.",
                response.status_code,
            )
            raise self.SecretsApiError()
