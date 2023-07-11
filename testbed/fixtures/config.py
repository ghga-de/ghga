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

"""The configuration for the test app."""

from pathlib import Path

from hexkit.config import config_from_yaml
from hexkit.providers.akafka import KafkaConfig
from hexkit.providers.mongodb import MongoDbConfig
from hexkit.providers.s3 import S3Config
from pydantic import SecretStr


@config_from_yaml(prefix="tb")
class Config(
    KafkaConfig,
    MongoDbConfig,
    S3Config,
):
    """Config class for the test app."""

    # directories
    base_dir: Path = Path(__file__).parent.parent
    data_dir = base_dir / "example_data"
    test_dir = base_dir / "test_data"

    # constants used in testing
    file_size: int = 20 * 1024**2

    # Kafka config
    service_name: str = "testbed_kafka"
    service_instance_id: str = "testbed-app-1"
    kafka_servers: list[str] = ["kafka:9092"]

    # MongoDb config
    db_connection_str: SecretStr = SecretStr(
        "mongodb://testbed_user:testbed_key@mongodb"
    )
    db_name: str = "test-db"
    # databases that shall be dropped after running the tests
    service_db_names: list[str] = ["ars", "auth", "dcs", "ifrs", "ucs", "wps"]
    service_kafka_topics: list[str] = [
        "downloads",
        "internal_registrations",
        "interrogations",
        "artifacts.embedded_public",
        "purges",
        "notifications",
    ]

    # S3 config
    s3_endpoint_url: str = "http://localstack:4566"
    s3_access_key_id: str = "testbed-key"
    s3_secret_access_key: SecretStr = SecretStr("testbed-secret")

    # file services
    file_metadata_event_topic: str = "metadata"
    file_metadata_event_type: str = "file_metadata_upserts"

    # bucket names
    inbox_bucket: str = "inbox"
    outbox_bucket: str = "outbox"
    staging_bucket: str = "staging"
    permanent_bucket: str = "permanent"

    object_id: str = "testbed-event-object"

    # file ingest
    file_ingest_url: str = "http://fis:8080/ingest"
    file_ingest_pubkey: str
