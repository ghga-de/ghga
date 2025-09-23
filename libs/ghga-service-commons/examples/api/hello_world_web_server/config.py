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

"""Config Parameter Modelling and Parsing."""

from functools import lru_cache

from hexkit.config import config_from_yaml
from pydantic import Field

from ghga_service_commons.api import ApiConfigBase


@config_from_yaml(prefix="hello_world")
class Config(ApiConfigBase):
    """Config parameters and their defaults."""

    # config parameter needed for the api server
    # are inherited from ApiConfigBase

    greeting: str = Field(
        default="World", description="Whom to greet in the application."
    )


@lru_cache
def get_config():
    """Get config parameter."""
    return Config()  # pyright: ignore
