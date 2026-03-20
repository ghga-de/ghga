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
"""HTTP exception classes for the GHGA Registry Service."""

from ghga_service_commons.httpyexpect.server.exceptions import HttpCustomExceptionBase


class HttpNotAuthorizedError(HttpCustomExceptionBase):
    """Raised when the caller is not authorized."""

    exception_id = "notAuthorized"

    def __init__(self):
        super().__init__(
            status_code=403,
            description="Not authorized.",
            data={},
        )


class HttpInternalError(HttpCustomExceptionBase):
    """Raised for unhandled internal errors."""

    exception_id = "internalError"

    def __init__(self):
        super().__init__(
            status_code=500,
            description="Internal server error.",
            data={},
        )
