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

import requests

from ghga_connector.core import exceptions
from ghga_connector.core.session import RequestsSession


def get_wps_file_info(
    *, work_package_id: str, token: str, wps_api_url: str
) -> dict[str, str]:
    """
    Call WPS endpoint and retrieve necessary information.
    For now, mock the call and return information from config.
    """

    url = f"{wps_api_url}/work-packages/{work_package_id}"

    # send authorization header as bearer token
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = RequestsSession.get(url=url, headers=headers)
    except requests.exceptions.RequestException as request_error:
        raise exceptions.RequestFailedError(url=url) from request_error

    status_code = response.status_code
    if status_code != 200:
        if status_code == 403:
            raise exceptions.NoWorkPackageAccessError(work_package_id=work_package_id)
        raise exceptions.BadResponseCodeError(url=url, response_code=status_code)

    response_body = response.json()

    return response_body["files"]
