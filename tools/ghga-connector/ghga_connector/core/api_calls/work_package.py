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
"""
This file contains all api calls related to obtaining work package and work order tokens
"""

from dataclasses import dataclass

import requests
from ghga_service_commons.utils.crypt import decrypt

from ghga_connector.core import exceptions
from ghga_connector.core.session import RequestsSession


@dataclass
class WorkPackageAccessor:
    """Wrapper for WPS associated API call parameters"""

    access_token: str
    api_url: str
    dcs_api_url: str
    package_id: str
    submitter_private_key: str

    def get_package_files(self) -> dict[str, str]:
        """
        Call WPS endpoint and retrieve work package information.
        """

        url = f"{self.api_url}/work-packages/{self.package_id}"

        # send authorization header as bearer token
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            response = RequestsSession.get(url=url, headers=headers)
        except requests.exceptions.RequestException as request_error:
            raise exceptions.RequestFailedError(url=url) from request_error

        status_code = response.status_code
        if status_code != 200:
            if status_code == 403:
                raise exceptions.NoWorkPackageAccessError(
                    work_package_id=self.package_id
                )
            raise exceptions.InvalidWPSResponseError(url=url, response_code=status_code)

        response_body = response.json()

        return response_body["files"]

    def get_work_order_token(self, *, file_id: str) -> str:
        """
        Call WPS endpoint to retrieve and decrypt work order token.
        """

        url = f"{self.api_url}/work-packages/{self.package_id}/files/{file_id}/work-order-tokens"

        # send authorization header as bearer token
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            response = RequestsSession.post(url=url, headers=headers)
        except requests.exceptions.RequestException as request_error:
            raise exceptions.RequestFailedError(url=url) from request_error

        status_code = response.status_code
        if status_code != 201:
            if status_code == 403:
                raise exceptions.NoWorkPackageAccessError(
                    work_package_id=self.package_id
                )
            raise exceptions.InvalidWPSResponseError(url=url, response_code=status_code)

        encrypted_token = response.content
        return _decrypt(data=encrypted_token, key=self.submitter_private_key)


def _decrypt(*, data: str, key: str):
    """Factored out decryption so this can be mocked."""
    return decrypt(data=data, key=key)
