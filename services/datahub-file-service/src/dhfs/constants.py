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

"""Constants to use for the DHFS"""

__all__ = [
    "AUTH_TAG_LENGTH",
    "AUTH_TOKEN_VALID_SECONDS",
    "DOWNLOAD_URL_CACHE_TIME",
    "DOWNLOAD_URL_LIFESPAN",
    "ENCRYPTION_SECRET_LENGTH",
    "HTTPX_TIMEOUT",
    "JWT_AUD",
    "JWT_ISS",
    "NONCE_LENGTH",
]

AUTH_TOKEN_VALID_SECONDS = 60
JWT_ISS = "GHGA"
JWT_AUD = "GHGA"
NONCE_LENGTH = 12
AUTH_TAG_LENGTH = 16
ENCRYPTION_SECRET_LENGTH = 32
DOWNLOAD_URL_LIFESPAN = 300  # five minutes
DOWNLOAD_URL_CACHE_TIME = DOWNLOAD_URL_LIFESPAN - 5
URL_CACHE_SIZE = 250
HTTPX_TIMEOUT = 60.0
