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

"""REST API specific config."""

from pydantic import Field
from pydantic_settings import BaseSettings


class TokenHashConfig(BaseSettings):
    """Config model containing a list of token hashes."""

    token_hashes: list[str] = Field(
        ...,
        description="List of token hashes corresponding to the tokens that can be used "
        + "to authenticate calls to this service.",
    )
