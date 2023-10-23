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

"""Make calls to the WKVS"""
from dataclasses import dataclass
from typing import Any

import httpx

from ghga_connector.core import exceptions
from ghga_connector.core.client import httpx_client
from ghga_connector.core.constants import TIMEOUT


@dataclass
class WKVSCaller:
    """Class to facilitate calls to WKVS (mainly just avoid providing URL repeatedly)"""

    wkvs_url: str  # base URL for the well-known-value-service

    def get_server_pubkey(self) -> str:
        """Retrieve the GHGA Crypt4GH public key"""
        return self._get_value("crypt4gh_public_key")

    def get_wps_api_url(self) -> str:
        """Retrieve the API URL for the WPS"""
        return self._get_api_url("wps")

    def get_dcs_api_url(self) -> str:
        """Retrieve the API URL for the DCS"""
        return self._get_api_url("dcs")

    def get_ucs_api_url(self) -> str:
        """Retrieve the API URL for the UCS"""
        return self._get_api_url("ucs")

    def _get_api_url(self, api_name: str) -> Any:
        return self._get_value(f"{api_name}_api_url").rstrip("/")

    def _get_value(self, value_name: str) -> Any:
        """Retrieve a value from the well-known-value-service.

        Args:
            value_name (str): the name of the value to be retrieved

        Raises:
            WellKnownValueNotFound: when a 404 response is received from the WKVS
            KeyError: when a successful response is received but doesn't contain the expected value

        """
        url = f"{self.wkvs_url}/values/{value_name}"

        try:
            with httpx_client() as client:
                response = client.get(url, timeout=TIMEOUT)  # verify is True by default
        except httpx.RequestError as request_error:
            exceptions.raise_if_connection_failed(request_error=request_error, url=url)
            raise exceptions.RequestFailedError(url=url) from request_error

        if response.status_code == 404:
            raise exceptions.WellKnownValueNotFound(value_name=value_name)

        try:
            value = response.json()[value_name]
        except KeyError as err:
            raise KeyError(
                "Response from well-known-value-service did not include expected field"
                + f" '{value_name}'"
            ) from err
        return value
