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

"""Config Parameter Modeling and Parsing"""

from ghga_service_commons.api import ApiConfigBase
from hexkit.config import config_from_yaml
from hexkit.log import LoggingConfig
from pydantic import Field, ValidationInfo, field_validator

from top.core.oidc_provider import OidcProviderConfig

SERVICE_NAME = "top"


@config_from_yaml(prefix=SERVICE_NAME)
class Config(ApiConfigBase, OidcProviderConfig, LoggingConfig):
    """Config parameters and their defaults."""

    service_name: str = Field(
        default=SERVICE_NAME, description="Short name of this service"
    )
    service_instance_id: str = Field(
        default="default",
        description=(
            "String that uniquely identifies this service instance in log messages"
        ),
    )

    @field_validator("cors_allowed_origins", mode="after")
    @classmethod
    def set_cors_allowed_origins(cls, value, info: ValidationInfo):
        """If no allowed origins are set, use appropriate defaults."""
        if value:
            return value
        url = info.data["redirect_url"]
        if url:
            origin = f"{url.scheme}://{url.host}"
            if (url.scheme, url.port) not in (("http", 80), ("https", 443)):
                origin += f":{url.port}"
            return [origin]
        return ["*"]

    @field_validator("cors_allowed_methods", mode="after")
    @classmethod
    def set_cors_allowed_methods(cls, value, info: ValidationInfo):
        """If no allowed methods are set, use appropriate defaults."""
        if value:
            return value
        return ["GET", "POST"]


CONFIG = Config()
