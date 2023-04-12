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
from ghga_service_commons.auth.ghga import AuthConfig
from hexkit.config import config_from_yaml
from hexkit.providers.mongodb import MongoDbConfig
from pydantic import SecretStr

from wps.core.repository import WorkPackageConfig


@config_from_yaml(prefix="wps")
class Config(
    ApiConfigBase, AuthConfig, MongoDbConfig, WorkPackageConfig
):  # pylint: disable=too-many-ancestors
    """Config parameters and their defaults."""

    service_name: str = "wps"
    db_name: str = "work-packages"

    # the default keys are invalid and only set for creating the example configuration
    # the public key for validating internal auth tokens
    auth_key: str = "{}"
    # the private key for signing work package access tokens
    work_package_signing_key: SecretStr = SecretStr("{}")
