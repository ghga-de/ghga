# Copyright 2021 - 2023 Universität Tübingen, DKFZ and EMBL
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

"""
Core utilities for the User Registry.
"""

__all__ = ["is_internal_id", "is_external_id"]


def is_internal_id(id_: str) -> bool:
    """Check if the passed ID is an internal user id."""
    if not id_ or not isinstance(id_, str):
        return False
    return len(id_) == 36 and id_.count("-") == 4 and "@" not in id_


def is_external_id(id_: str) -> bool:
    """Check if the passed ID is an external user id."""
    if not id_ or not isinstance(id_, str):
        return False
    return len(id_) > 8 and id_.count("@") == 1
