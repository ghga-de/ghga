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
#

"""General purpose validation logic used by both the client and server side."""


import re
from typing import Optional

from ghga_service_commons.httpyexpect.base_exception import HttpyExpectError
from ghga_service_commons.httpyexpect.models import EXCEPTION_ID_PATTERN


class ValidationError(HttpyExpectError):
    """Thrown when a exception mapping spec failed validation."""


def assert_error_code(status_code: object) -> None:
    """Check that the provided status code corresponds to a valid error code."""
    if not isinstance(status_code, int) or not 400 <= status_code < 600:
        raise ValidationError(
            "The status codes must correspond to an HTTP exception (4xx or 5xx),"
            + f" obtained: {status_code}"
        )


def validate_exception_id(
    exception_id: object,
    *,
    status_code: Optional[int] = None,
) -> None:
    """Check the format of an exception id."""
    if not isinstance(exception_id, str) or not re.match(
        EXCEPTION_ID_PATTERN, exception_id
    ):
        raise ValidationError(
            "The exception ID must be a string formatted according to the regex"
            + f"{EXCEPTION_ID_PATTERN}, however,"
            + (f"for the status code {status_code}," if status_code else "")
            + f" the following was given: {exception_id}"
        )
