# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

from typing import Optional

from ghga_service_chassis_lib.api import ApiConfigBase, LogLevel
from ghga_service_chassis_lib.config import config_from_yaml


@config_from_yaml(prefix="auth_service")
class Config(ApiConfigBase):
    """Config parameters and their defaults."""

    service_name: str = "auth_service"
    log_level: LogLevel = "info"
    run_auth_adapter: bool = False
    auth_path_prefix: str = "/auth"
    basic_auth_user: Optional[str] = None
    basic_auth_pwd: Optional[str] = None


CONFIG = Config()
