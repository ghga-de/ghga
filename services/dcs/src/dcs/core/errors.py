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

"""Shared error classes used across the core domain."""


class StorageAliasNotConfiguredError(RuntimeError):
    """Raised when looking up an object storage configuration by alias fails."""

    def __init__(self, *, alias: str):
        message = (
            f"Could not find a storage configuration for alias {alias}.\n"
            + "Check íf your multi node configuration contains a corresponding entry."
        )
        super().__init__(message)
