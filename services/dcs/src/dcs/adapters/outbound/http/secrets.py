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

"""Secrets API client class implementation"""

import base64
import logging

import httpx
from pydantic import Field
from pydantic_settings import BaseSettings

from dcs.adapters.outbound.http import exceptions
from dcs.adapters.outbound.http.exception_translation import ResponseExceptionTranslator
from dcs.constants import TRACER
from dcs.ports.outbound.secrets import SecretsClientPort

log = logging.getLogger(__name__)


class SecretsClientConfig(BaseSettings):
    """Configuration for the Secrets Client"""

    ekss_base_url: str = Field(
        default=...,
        description=(
            "URL containing host and port of the EKSS endpoint to retrieve"
            + " personalized envelope from"
        ),
        title="EKSS base URL",
        examples=["http://ekss:8080/"],
    )


class SecretsClient(SecretsClientPort):
    """A class to communicate with the Secrets API regarding file encryption secrets"""

    def __init__(self, *, config: SecretsClientConfig, httpx_client: httpx.AsyncClient):
        """Initialize the SecretsClient"""
        self._httpx_client = httpx_client
        self._api_base = config.ekss_base_url

    # The method name no longer references EKSS, but we'll leave it in the span name
    @TRACER.start_as_current_span("api_calls.get_envelope_from_ekss")
    async def get_envelope(self, *, secret_id: str, receiver_public_key: str) -> str:
        """Call the Secrets API to get an envelope for an encrypted file, using the
        receiver's public key as well as the id of the file secret.

        Raises:
            RequestFailedError: if an error prevents obtaining a response.
            BadResponseCodeError: if a response is received but the status code
                indicates that the request was unsuccessful.
        """
        receiver_public_key_base64 = base64.urlsafe_b64encode(
            base64.b64decode(receiver_public_key)
        ).decode()
        api_url = f"{self._api_base}/secrets/{secret_id}/envelopes/{receiver_public_key_base64}"
        try:
            response = await self._httpx_client.get(url=api_url)
        except httpx.RequestError as err:
            request_failed_error = exceptions.RequestFailedError(url=api_url)
            log.error(
                request_failed_error,
                extra={
                    "secret_id": secret_id,
                    "receiver_public_key": receiver_public_key,
                },
            )
            raise request_failed_error from err

        status_code = response.status_code
        # implement httpyexpect error conversion
        if status_code != 200:
            spec: dict[int, object] = {
                404: {
                    "secretNotFoundError": lambda: exceptions.SecretNotFoundError(
                        secret_id=secret_id
                    )
                },
            }
            ResponseExceptionTranslator(spec=spec).handle(response=response)
            bad_code_error = exceptions.BadResponseCodeError(
                url=self._api_base, response_code=status_code
            )
            log.error(
                bad_code_error,
                extra={"response_code": status_code, "secret_id": secret_id},
            )
            raise bad_code_error

        body = response.json()
        content = body["content"]

        return content

    # The method name no longer references EKSS, but we'll leave it in the span name
    @TRACER.start_as_current_span("api_calls.delete_secret_from_ekss")
    async def delete_secret(self, *, secret_id: str) -> None:
        """Call the Secrets API to delete a file secret

        Raises:
            RequestFailedError: if an error prevents obtaining a response.
            BadResponseCodeError: if a response is received but the status code
                indicates that the request was unsuccessful.
        """
        api_url = f"{self._api_base}/secrets/{secret_id}"

        try:
            response = await self._httpx_client.delete(url=api_url)
        except httpx.RequestError as err:
            request_failed_error = exceptions.RequestFailedError(url=api_url)
            log.error(
                request_failed_error,
                extra={"secret_id": secret_id},
            )
            raise request_failed_error from err

        status_code = response.status_code

        # implement httpyexpect error conversion
        if status_code != 204:
            spec: dict[int, object] = {
                404: {
                    "secretNotFoundError": lambda: exceptions.SecretNotFoundError(
                        secret_id=secret_id
                    )
                },
            }
            ResponseExceptionTranslator(spec=spec).handle(response=response)
            bad_code_error = exceptions.BadResponseCodeError(
                url=self._api_base, response_code=status_code
            )
            log.error(
                bad_code_error,
                extra={"response_code": status_code, "secret_id": secret_id},
            )
            raise bad_code_error
