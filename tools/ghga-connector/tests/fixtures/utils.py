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

"""Utils for Fixture handling"""


from pathlib import Path
from typing import Any

import crypt4gh.keys
from ghga_service_commons.utils import crypt

BASE_DIR = Path(__file__).parent.resolve()
KEY_DIR = BASE_DIR / "keypair"
PUBLIC_KEY_FILE = KEY_DIR / "key.pub"
PRIVATE_KEY_FILE = KEY_DIR / "key.sec"


def mock_wps_token(max_tries: int, message_display: Any) -> list[str]:
    """
    Helper to mock user input
    """

    work_package_id = "wp_1"
    token = "abcde"

    public_key = crypt4gh.keys.get_public_key(PUBLIC_KEY_FILE)

    wps_token = [work_package_id, crypt.encrypt(token, public_key)]
    return wps_token
