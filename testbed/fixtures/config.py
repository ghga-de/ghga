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
from urllib.parse import urljoin

from hexkit.config import config_from_yaml
from hexkit.providers.akafka import KafkaConfig
from hexkit.providers.mongodb import MongoDbConfig
from hexkit.providers.s3 import S3Config
from pydantic import Field, SecretStr, root_validator


@config_from_yaml(prefix="tb")
class Config(KafkaConfig, MongoDbConfig, S3Config):
    """Config class for the test app."""

    # operation modes
    use_api_gateway: bool = Field(
        False, description="set to True for black-box testing"
    )
    use_auth_adapter: bool = Field(
        True, description="set to True for token exchange via auth adapter"
    )
    keep_state_in_db: bool = Field(
        True, description="set to True for saving state permanently"
    )

    # directories
    base_dir: Path = Path(__file__).parent.parent
    data_dir = base_dir / "example_data"
    test_dir = base_dir / "test_data"

    # constants used in testing
    upload_part_size: int = 1024
    download_part_size: int = 8589934592
    default_file_size: int = 20 * upload_part_size**2

    # Kafka config
    service_name: str = "testbed_kafka"
    service_instance_id: str = "testbed-app-1"
    kafka_servers: list[str] = ["kafka:9092"]  # noqa: RUF012

    # MongoDb config
    db_connection_str: SecretStr = SecretStr(
        "mongodb://testbed_user:testbed_key@mongodb"
    )
    db_name: str = "test-db"
    # databases that shall be dropped when running from scratch
    service_db_names: list[str] = [  # noqa: RUF012
        "ars",
        "auth",
        "dcs",
        "ifrs",
        "metldata",
        "ucs",
        "wps",
        "mass",
    ]

    # S3 config
    s3_endpoint_url: str = "http://localstack:4566"
    s3_access_key_id: str = "testbed-key"
    s3_secret_access_key: SecretStr = SecretStr("testbed-secret")

    # bucket names
    inbox_bucket: str = "inbox"
    outbox_bucket: str = "outbox"
    staging_bucket: str = "staging"
    permanent_bucket: str = "permanent"

    object_id: str = "testbed-event-object"

    # external base URL
    external_base_url: str = ""
    external_apis: list[str] = [  # noqa: RUF012
        "wkvs",
        "dcs",
        "fis",
        "metldata",
        "ars",
        "ums",
        "wps",
        "mass",
        "mail",
        "op",
    ]

    # internal APIs
    internal_apis: list[str] = ["ekss", "auth_adapter"]  # noqa: RUF012

    # auth
    auth_key_file = Path(__file__).parent.parent / ".devcontainer/auth.env"
    auth_adapter_url: str = "http://auth:8080"
    auth_basic: str = ""  # for Basic Authentication
    upload_token: str = ""  # simple token for uploading metadata

    # wkvs
    wkvs_url: str = "http://wkvs"

    # connector
    user_private_crypt4gh_key: str
    user_public_crypt4gh_key: str

    # dskit
    dsk_token_path: Path = Path.home() / ".ghga_data_steward_token.txt"

    # file ingest
    fis_url: str = "http://fis:8080"
    fis_pubkey: str

    # metldata
    metldata_db_name: str = "metldata"
    metldata_url: str = "http://metldata:8080"

    # ars
    ars_db_name: str = "ars"
    ars_url: str = "http://ars:8080"

    # ums
    ums_db_name: str = "auth"
    ums_users_collection: str = "users"
    ums_claims_collection: str = "claims"
    ums_url: str = "http://ums:8080"

    # wps
    wps_db_name: str = "wps"
    wps_url: str = "http://wps:8080"

    # ifrs
    ifrs_db_name: str = "ifrs"
    ifrs_metadata_collection: str = "file_metadata"

    # mass
    mass_url: str = "http://mass:8080"

    # notifications
    mail_url: str = "http://mailhog:8025"

    # test OP
    op_url: str = "http://op.test"
    op_issuer: str = "https://test-aai.ghga.de"

    # ekss
    ekss_url: str = "http://ekss"

    # dcs
    dcs_url: str = "http://dcs:8080"

    @root_validator(pre=False)
    @classmethod
    def check_operation_modes(cls, values):
        """Check that operation modes are not conflicting."""
        try:
            if values["use_api_gateway"]:
                if not values["use_auth_adapter"]:
                    raise ValueError("API gateway always uses auth adapter")
            elif values["auth_basic"]:
                raise ValueError("Basic auth must only be used with API gateway")
        except (KeyError, ValueError) as error:
            raise ValueError(f"Check operation modes: {error}") from error
        return values

    @root_validator(pre=False)
    @classmethod
    def add_external_base_url(cls, values):
        """Add base URL to all APIs.

        This allows the URLs to be specified as paths relative to the external base URL
        to avoid repetition in the external mode configuration.
        """
        base_url = values["external_base_url"]
        apis = values["external_apis"] + values["internal_apis"]
        if base_url and apis:
            if not base_url.startswith(("http://", "https://")):
                raise ValueError("External base URL must be absolute")
            base_url = base_url.rstrip("/")

            for api in apis:
                key = f"{api}_url"
                try:
                    url = values[key]
                    if not url:
                        raise KeyError("URL is empty")
                except KeyError as error:
                    raise ValueError(f"Missing value for {key}") from error
                if "://" not in url:
                    url = base_url + "/" + url.lstrip("/")
                    values[key] = url
        return values
