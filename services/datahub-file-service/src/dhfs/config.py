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

"""Config Parameter Modeling and Parsing."""

from pathlib import Path

from ghga_service_commons.transports import CompositeCacheConfig
from hexkit.config import config_from_yaml
from hexkit.log import LoggingConfig
from hexkit.providers.s3 import S3Config
from pydantic import Field
from pydantic_settings import BaseSettings

from dhfs.adapters.outbound.central import CentralClientConfig

SERVICE_NAME: str = "dhfs"


class Crypt4GHConfig(BaseSettings):
    """Service specific configuration"""

    data_hub_crypt4gh_private_key_path: Path = Field(
        default=...,
        examples=["./key.sec"],
        description="Path to the Data Hub's Crypt4GH private key file",
    )
    crypt4gh_private_key_passphrase: str | None = Field(
        default=None,
        description=(
            "Passphrase needed to read the content of the private key file. "
            + "Only needed if the private key is encrypted."
        ),
    )


@config_from_yaml(prefix=SERVICE_NAME)
class Config(
    LoggingConfig,
    S3Config,
    CentralClientConfig,
    CompositeCacheConfig,
    Crypt4GHConfig,
):
    """Config parameters and their defaults."""

    min_run_interval_seconds: int = Field(
        default=60,
        description=(
            "The minimum number of seconds to wait before asking the CentralAPI"
            + " about new files for interrogation."
        ),
    )

    interrogation_bucket_id: str = Field(
        default="interrogation",
        description="The name for the S3 'interrogation' bucket",
    )
    service_name: str = Field(
        default=SERVICE_NAME, description="Short name of this service"
    )


CONFIG = Config()  # type: ignore
