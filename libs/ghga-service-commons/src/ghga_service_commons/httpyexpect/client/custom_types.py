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

"""Custom types and type aliases."""

from collections.abc import Mapping
from typing import Any, Callable, Literal, Protocol

ExceptionFactoryParam = Literal["status_code", "exception_id", "description", "data"]
StatusCode = int
ExceptionId = str
ExceptionFactory = Callable[..., Exception]
ExceptionMappingSpec = Mapping[StatusCode, object]


class Response(Protocol):
    """Any Response that is compatible with httpx and requests."""

    status_code: int
    """Status code of the Response"""

    def json(self, **kwargs: Any) -> Any:
        """JSON representation of the Response."""
        ...
