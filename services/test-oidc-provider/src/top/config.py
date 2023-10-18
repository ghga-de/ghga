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

"""Config Parameter Modeling and Parsing"""

from ghga_service_commons.api import ApiConfigBase
from hexkit.config import config_from_yaml
from pydantic import AnyHttpUrl, Field

from top.core.oidc_provider import OidcProviderConfig

SERVICE_NAME = "top"


@config_from_yaml(prefix=SERVICE_NAME)
class Config(ApiConfigBase, OidcProviderConfig):
    """Config parameters and their defaults."""

    service_name: str = Field(SERVICE_NAME, description="Short name of this service")
    service_url: AnyHttpUrl = Field(
        "https://op.test",  # pyright: ignore
        description="External base URL of this service",
    )


CONFIG = Config()  # type: ignore
