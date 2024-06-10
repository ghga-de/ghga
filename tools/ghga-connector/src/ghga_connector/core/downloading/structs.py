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
#
"""Contains additional data structures needed by the download code"""

from dataclasses import dataclass

from httpx import Headers


@dataclass
class RetryResponse:
    """Response to download request if file is not yet staged"""

    retry_after: int


@dataclass
class URLResponse:
    """Response to download request, containing file size and presigned object storage URL for download"""

    download_url: str
    file_size: int


@dataclass
class UrlAndHeaders:
    """Combination of endpoint url and headers needed to make an authorized call against the endpoint"""

    endpoint_url: str
    headers: Headers
