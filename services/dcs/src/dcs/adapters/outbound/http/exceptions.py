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
"""Service specific exceptions"""


class KnownError(RuntimeError):
    """Base class for custom errors encountered"""


class BadResponseCodeError(KnownError):
    """Thrown, when a request returns an unexpected response code (e.g. 500)"""

    def __init__(self, *, url: str, response_code: int):
        self.response_code = response_code
        message = f"The request to {url} failed with response code {response_code}"
        super().__init__(message)


class RequestFailedError(KnownError):
    """Thrown when a request fails without returning a response code"""

    def __init__(self, *, url: str):
        message = f"The request to {url} failed."
        super().__init__(message)


class SecretNotFoundError(KnownError):
    """Thrown when the secret with the id was not found"""

    def __init__(self, *, secret_id):
        message = f"The secret with the id {secret_id} was not found."
        super().__init__(message)
