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

import base64
from dataclasses import dataclass


@dataclass
class WPSInfo:
    """
    Container for WPS endpoint information
    """

    file_ids_with_extension: dict[str, str]
    ghga_pubkey: bytes
    user_id: str
    user_pubkey: bytes


def get_wps_info(config):
    """
    Call WPS endpoint and retrieve necessary information.
    For now, mock the call and return information from config.
    """
    ghga_pubkey = base64.b64decode(config.server_pubkey)
    user_pubkey = base64.b64decode(config.wps_user_pubkey)

    file_ids_with_ending = dict(zip(config.wps_file_list, config.wps_file_endings))

    wps_info = WPSInfo(
        file_ids_with_extension=file_ids_with_ending,
        ghga_pubkey=ghga_pubkey,
        user_id=config.wps_user_id,
        user_pubkey=user_pubkey,
    )
    return wps_info
