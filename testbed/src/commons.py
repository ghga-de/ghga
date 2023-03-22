# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Common constants for use in other modules"""

from pathlib import Path

from hexkit.config import config_from_yaml
from hexkit.providers.akafka import KafkaConfig
from hexkit.providers.s3 import S3Config


@config_from_yaml(prefix="tb")
class Config(S3Config, KafkaConfig):
    """
    Custom Config class for the test app.
    Defaults set for not running inside devcontainer.
    """

    db_connection_str: str
    file_metadata_event_topic: str
    file_metadata_event_type: str
    inbox_bucket: str


BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "example_data"
TEST_DIR = BASE_DIR / "test_data"
CONFIG = Config()
FILE_SIZE = 20 * 1024**2
