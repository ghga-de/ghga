# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
from hexkit.providers.s3 import S3Config
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings


class Buckets(BaseModel):
    """Configuration for S3 bucket IDs."""

    inbox: str
    outbox: str
    staging: str
    permanent: str

    def __iter__(self):
        """Allow iteration over all bucket IDs."""
        return iter([self.inbox, self.outbox, self.staging, self.permanent])


class S3StorageConfig(BaseModel):
    """Configuration for an S3 object storage."""

    storage_alias: str
    credentials: S3Config
    buckets: Buckets


class ObjectStoragesConfig(BaseModel):
    """Configuration for multiple S3 object storages."""

    primary: S3StorageConfig
    secondary: S3StorageConfig


@config_from_yaml(prefix="tb")
class Config(BaseSettings):
    """Config class for the test app."""

    # operation modes
    use_api_gateway: bool = Field(
        False, description="set to True for black-box testing"
    )
    keep_state_in_db: bool = Field(
        True, description="set to True for saving state permanently"
    )

    # directories
    base_dir: Path = Path(__file__).parent.parent
    data_dir: Path = base_dir / "example_data"
    test_dir: Path = base_dir / "test_data"

    # constants used in testing
    upload_part_size: int = 1024
    download_part_size: int = 8589934592
    default_file_size: int = 20 * upload_part_size**2

    # databases that shall be dropped when running from scratch
    service_db_names: list[str] = [
        "ars",
        "auth",
        "dcs",
        "ifrs",
        "metldata",
        "ucs",
        "wps",
        "mass",
        "nos",
        "ns",
        "fis",
        "dins",
        "pcs",
        "dlq",
    ]

    object_storages: ObjectStoragesConfig = ObjectStoragesConfig(
        **{
            "primary": {
                "storage_alias": "primary",
                "credentials": {
                    "s3_endpoint_url": "http://localstack-1:4566",
                    "s3_access_key_id": "testbed-key",
                    "s3_secret_access_key": "testbed-secret",
                },
                "buckets": {
                    "inbox": "hub1-inbox",
                    "outbox": "hub1-outbox",
                    "staging": "hub1-interrogations",
                    "permanent": "hub1-permanent",
                },
            },
            "secondary": {
                "storage_alias": "secondary",
                "credentials": {
                    "s3_endpoint_url": "http://localstack-2:4566",
                    "s3_access_key_id": "testbed-key",
                    "s3_secret_access_key": "testbed-secret",
                },
                "buckets": {
                    "inbox": "hub2-inbox",
                    "outbox": "hub2-outbox",
                    "staging": "hub2-interrogations",
                    "permanent": "hub2-permanent",
                },
            },
        }  # type: ignore
    )

    object_id: str = "testbed-event-object"

    # external base URL
    external_base_url: str = ""
    external_apis: list[str] = [
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
        "sms",
        "dins",
        "pcs",
        "dlq",
    ]

    # internal APIs
    internal_apis: list[str] = ["ekss", "auth_adapter"]

    # auth
    auth_key_file: Path = Path(__file__).parent.parent / ".devcontainer/auth.env"
    auth_adapter_url: str = "http://auth"
    auth_basic: str = ""  # for Basic Authentication
    upload_token: str = ""  # simple token for uploading metadata
    state_management_token: str = ""  # simple token for state management service
    purge_controller_token: str = ""  # simple token for purge controller service
    dlq_token: str = ""  # simple token for dlq service
    totp_digits: int = 6
    totp_algorithm: str = "sha1"
    totp_interval: int = 30

    # wkvs
    wkvs_url: str = "http://wkvs"

    # connector
    user_private_crypt4gh_key: str
    user_public_crypt4gh_key: str

    # dskit
    dsk_token_path: Path = Path.home() / ".ghga_data_steward_token.txt"

    # file ingest
    fis_url: str = "http://fis"
    fis_pubkey: str
    fis_db_name: str = "fis"
    fis_ingested_files_collection: str = "ingestedFiles"

    # metldata
    metldata_db_name: str = "metldata"
    metldata_url: str = "http://metldata"

    # ars
    ars_db_name: str = "ars"
    ars_url: str = "http://ars"

    # ums
    ums_db_name: str = "auth"
    ums_users_collection: str = "users"
    ums_claims_collection: str = "claims"
    ums_user_tokens_collection: str = "user_tokens"
    ums_user_ivas_collection: str = "ivas"
    ums_url: str = "http://ums"

    # wps
    wps_db_name: str = "wps"
    wps_url: str = "http://wps"

    # ifrs
    ifrs_db_name: str = "ifrs"
    ifrs_metadata_collection: str = "file_metadata"
    ifrs_file_metadata_collection: str = "file_metadata"

    # pcs
    pcs_db_name: str = "pcs"
    pcs_file_deletion_event_collection: str = "pcsPersistedEvents"
    pcs_url: str = "http://pcs"

    # mass
    mass_url: str = "http://mass"

    # notification orchestration
    nos_db_name: str = "nos"

    # notifications
    mail_url: str = "http://mailhog:8025"

    # test OP
    op_url: str = "http://op.test"
    op_issuer: str = "https://test-aai.ghga.dev"

    # ekss
    ekss_url: str = "http://ekss"

    # dcs
    dcs_url: str = "http://dcs"
    dcs_db_name: str = "dcs"
    dcs_objects_collection: str = "drs_objects"

    # data portal ui
    data_portal_url: str = "http://data-portal"

    # vault
    vault_path: str = "testing"

    # sms
    sms_url: str = "http://sms"

    # dins
    dins_url: str = "http://dins"
    dins_db_name: str = "dins"
    dins_metadata_collection: str = "file_information"

    # event topics
    file_interrogations_topic: str = "interrogations"

    # dlq
    dlq_url: str = "http://dlq"
    dlq_topic: str = "dlq"
    dlq_db_name: str = "dlqs"
    dlq_events_collection: str = "dlqEvents"

    dataset_change_topic: str = "metadata-datasets"
    dataset_created_type: str = "dataset_created"
    file_deletion_request_topic: str = "purges"
    file_deletion_request_type: str = "file_deletion_requested"
    access_request_topic: str = "access-requests"
    access_request_created_type: str = "access_request_created"
    resource_change_topic: str = "searchable-resources"
    resource_change_type: str = "searchable_resource_upserted"
    notification_topic: str = "notifications"
    notification_type: str = "notification"

    service_short_names: dict[str, str] = {
        "work package service": "wps",
        "dataset information service": "dins",
        "download controller service": "dcs",
        "internal file registry service": "internal_file_registry",
        "notification orchestration service": "nos",
        "notification service": "ns",
        "metadata artifact search service": "mass",
    }

    @model_validator(mode="after")
    def check_operation_modes(self):
        """Check that operation modes are not conflicting."""
        if not self.use_api_gateway and self.auth_basic:
            error = "Basic auth must only be used with API gateway"
            raise ValueError(f"Check operation modes: {error}")
        return self

    @model_validator(mode="after")
    def add_external_base_url(self):
        """Add base URL to all APIs.

        This allows the URLs to be specified as paths relative to the external base URL
        to avoid repetition in the external mode configuration.
        """
        base_url = self.external_base_url
        apis = self.external_apis + self.internal_apis
        if base_url and apis:
            if not base_url.startswith(("http://", "https://")):
                raise ValueError("External base URL must be absolute")
            base_url = base_url.rstrip("/")

            for api in apis:
                attr = f"{api}_url"
                try:
                    url = getattr(self, attr)
                    if not url:
                        raise KeyError("URL is empty")
                except KeyError as error:
                    raise ValueError(f"Missing value for {attr}") from error
                if "://" not in url:
                    url = base_url + "/" + url.lstrip("/")
                    # instance already frozen, can only be changed via dict
                    self.__dict__[attr] = url
        return self
