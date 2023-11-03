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

"""Global Config Parameters"""

from hexkit.config import config_from_yaml
from pydantic import Field
from pydantic_settings import BaseSettings

from ghga_connector.core.constants import DEFAULT_PART_SIZE, MAX_RETRIES, MAX_WAIT_TIME


@config_from_yaml(prefix="ghga_connector")
class Config(BaseSettings):
    """Global Config Parameters"""

    max_retries: int = Field(
        MAX_RETRIES, description="Number of times to retry failed API calls."
    )
    max_wait_time: int = Field(
        MAX_WAIT_TIME,
        description="Maximal time in seconds to wait before quitting without a download.",
    )
    part_size: int = Field(
        DEFAULT_PART_SIZE, description="The part size to use for download."
    )
    wkvs_api_url: str = Field(
        "https://data.ghga.de/.well-known",
        description="URL to the root of the WKVS API. Should start with https://",
    )
