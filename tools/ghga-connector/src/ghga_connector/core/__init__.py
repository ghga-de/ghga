# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
This sub-package contains the main business functionality of this service.
It should not contain any service API-related code.
"""

from .client import async_client, httpx_client, retry_handler  # noqa: F401
from .file_operations import (  # noqa: F401
    calc_part_ranges,
    get_segments,
    is_file_encrypted,
    read_file_parts,
)
from .http_translation import ResponseExceptionTranslator  # noqa: F401
from .message_display import AbstractMessageDisplay, MessageColors  # noqa: F401
from .structs import PartRange  # noqa: F401
from .work_package import WorkPackageAccessor  # noqa: F401
