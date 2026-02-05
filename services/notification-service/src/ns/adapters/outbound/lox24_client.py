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
#

"""Contains the sms client adapter"""

import logging

from httpx import URL, HTTPStatusError, Response, post
from pydantic import Field, HttpUrl, PositiveFloat, SecretStr
from pydantic_settings import BaseSettings

from ns.ports.outbound.sms_client import SmsClientPort

log = logging.getLogger(__name__)


class Lox24ClientConfig(BaseSettings):
    """Configuration details for the Lox24Client"""

    lox24_base_url: HttpUrl = Field(
        default="https://api.lox24.eu:443", description="The base URL of the lox24 API"
    )  # type: ignore
    lox24_token: SecretStr = Field(default=..., description="The authentication token")
    lox24_timeout: PositiveFloat | None = Field(
        default=10,
        description=(
            "The maximum amount of time (in seconds) to wait for a connection to the"
            + " lox24 API. If set to `None`, the operation will wait indefinitely."
        ),
    )
    lox24_send_sms_path: str = Field(
        default="sms", description="The path for sending SMS messages"
    )
    lox24_auth_token_header: str = Field(
        default="X-LOX24-AUTH-TOKEN",
        description="The header for the authentication token",
    )
    lox24_sender_id: str = Field(
        default="GHGA", description="The sender ID to use when sending SMS messages"
    )

    @property
    def lox24_send_url(self) -> URL:
        """Full URL for sending SMS."""
        url = URL(str(self.lox24_base_url))
        url = url.join(self.lox24_send_sms_path)
        return url


class Lox24Client(SmsClientPort):
    """Concrete implementation of an SmsClientPort for the LOX24 SMS gateway."""

    def __init__(self, *, config: Lox24ClientConfig):
        """Assign config, which should contain all needed info"""
        self._config = config
        self._response: Response | None = None
        self._sender_id: str = self._config.lox24_sender_id
        self._send_url: URL = self._config.lox24_send_url
        self._headers: dict[str, str] = {
            self._config.lox24_auth_token_header: self._config.lox24_token.get_secret_value()
        }

    def _raise_for_status(self, response: Response):
        """Raise an exception if the response indicates an error."""
        if response:
            try:
                response.raise_for_status()
            except HTTPStatusError as err:
                match err.response.status_code:
                    case 400 | 404 | 422:
                        raise SmsClientPort.RequestError() from err
                    case 401 | 402 | 403 | 429:
                        raise SmsClientPort.AccountError() from err
                    case 500 | 502 | 503 | 504:
                        raise SmsClientPort.SystemError() from err
                    case _:
                        raise SmsClientPort.GeneralSmsException(
                            error_info=str(err)
                        ) from err

    def send_sms_message(self, *, phone: str, text: str):
        """Send an SMS message to the Lox24 API."""
        json_data = {
            "phone": phone,
            "text": text,
            "sender_id": self._sender_id,
        }
        log.info(f"Sending SMS to {phone}.")
        response = post(
            self._send_url,
            headers=self._headers,
            json=json_data,
            timeout=self._config.lox24_timeout,
        )
        try:
            if response.status_code != 201:
                self._raise_for_status(response)
        except Exception as err:
            log.error(
                "Received a %i status code when trying to send SMS. Response payload: %s",
                response.status_code,
                response.json(),
                exc_info=True,
            )
            raise err
        uuid = response.json().get("uuid", "unknown")
        log.info(f"SMS sent to {phone}. Response UUID {uuid}")
