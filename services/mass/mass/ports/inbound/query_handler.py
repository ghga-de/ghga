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
"""Contains the port for a query handler"""

from abc import ABC, abstractmethod
from typing import Optional

from mass.core import models


class ClassNotConfiguredError(RuntimeError):
    """Raised when searching for class_name that isn't configured"""

    def __init__(self, class_name: str):
        message = f"Class with name '{class_name}' not configured."
        super().__init__(message)


class SearchError(RuntimeError):
    """Raised when there is a problem searching with the query parameters."""

    def __init__(self):
        super().__init__(
            "Error executing search. Possibly a problem with the supplied parameters."
        )


class QueryHandlerPort(ABC):
    """Port for the query handler"""

    @abstractmethod
    async def handle_query(
        self,
        *,
        class_name: str,
        query: str,
        filters: list[models.Filter],
        skip: int,
        limit: Optional[int] = None,
    ):
        """Processes a query"""
        ...
