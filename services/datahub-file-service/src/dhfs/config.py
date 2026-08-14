# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

import logging
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings

from dhfs.adapters.outbound.central import CentralClientConfig
from dhfs.adapters.outbound.http import HttpClientConfig
from dhfs.constants import SQUASHED_LOGGERS
from hexkit.config import config_from_yaml
from hexkit.log import LoggingConfig, LogLevel
from hexkit.providers.s3 import S3Config

SERVICE_NAME: str = "dhfs"

log = logging.getLogger(__name__)


class Crypt4GHConfig(BaseSettings):
    """Service specific configuration"""

    data_hub_crypt4gh_private_key_path: Path = Field(
        default=...,
        examples=["./key.sec"],
        description="Path to the Data Hub's Crypt4GH private key file",
    )
    data_hub_crypt4gh_private_key_passphrase: str | None = Field(
        default=None,
        description=(
            "Passphrase needed to read the content of the private key file. "
            + "Only needed if the private key is encrypted."
        ),
    )


class VerifierConfig(BaseSettings):
    """Additional S3 credentials with write access to the inbox bucket.

    These are only required when running `dhfs verify`. DHFS normally has
    read-only access to the inbox; these credentials are used solely to upload and
    subsequently delete the dummy file used for verification.
    """

    data_hub_crypt4gh_public_key_path: Path | None = Field(
        default=None,
        examples=["./key.pub"],
        description=(
            "Path to the Data Hub's Crypt4GH public key file. Only needed for"
            + " running `dhfs verify`."
        ),
    )
    inbox_bucket_id: str | None = Field(
        default=None,
        examples=["inbox", "hub-inbox"],
        description="The inbox bucket ID - only needed for running `dhfs verify`.",
    )
    inbox_write_s3_access_key_id: str | None = Field(
        default=None,
        examples=["my-write-access-key-id"],
        description=(
            "S3 access key ID with write access to the inbox bucket."
            + " Only needed for running `dhfs verify`."
        ),
    )
    inbox_write_s3_secret_access_key: SecretStr | None = Field(
        default=None,
        description=(
            "S3 secret access key with write access to the inbox bucket."
            + " Only needed for running `dhfs verify`."
        ),
    )
    inbox_write_s3_session_token: SecretStr | None = Field(
        default=None,
        description=(
            "Optional S3 session token for the write-capable inbox credentials."
            + " Only needed for running `dhfs verify`."
        ),
    )


@config_from_yaml(prefix=SERVICE_NAME)
class Config(
    LoggingConfig,
    S3Config,
    CentralClientConfig,
    Crypt4GHConfig,
    VerifierConfig,
    HttpClientConfig,
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
        default=...,
        description=(
            "The name for the S3 'interrogation' bucket, which houses re-encrypted"
            + " files until they are copied to permanent storage by IFRS."
        ),
    )

    max_concurrent_files: int = Field(
        default=2,
        ge=1,
        description=(
            "How many files from a batch to process at the same time. This bounds how"
            + " many multipart uploads are open at once. It does not affect memory use:"
            + " that is governed by max_concurrent_parts alone."
        ),
    )

    max_concurrent_parts: int = Field(
        default=8,
        ge=1,
        description=(
            "How many file parts to process at the same time, counted across all files"
            + " being processed concurrently. This lets the download of one part overlap"
            + " the re-encryption of another and the upload of a third, and it is the"
            + " service's memory budget: peak use is roughly max_concurrent_parts * 3 *"
            + " the part size, no matter how many files are in flight. Files share the"
            + " budget, so a single large file can use all of it."
        ),
    )

    max_concurrent_deletions: int = Field(
        default=16,
        ge=1,
        description=(
            "How many objects the cleanup routine deletes from the interrogation"
            + " bucket at the same time. Each deletion is its own request, so a serial"
            + " cleanup costs one round trip per object. Deletions hold no file data,"
            + " so this only trades against load on the S3 backend."
        ),
    )

    service_name: str = Field(
        default=SERVICE_NAME, description="Short name of this service"
    )

    library_log_level: LogLevel = Field(
        default="CRITICAL",
        description=(
            "The log level to use for libraries. This option can be used in tandem with"
            + " log_level to view DEBUG logs from DHFS without the noise of third-party"
            + " libraries. Will be overridden by log_level if log_level is higher."
            + " By default, this is set to CRITICAL, which will suppress all logs"
            + " with a log level lower than CRITICAL."
        ),
    )

    library_logger_names: list[str] = Field(
        default=SQUASHED_LOGGERS,
        description="The list of logger names to target with library_log_level.",
    )

    @field_validator("client_reraise_from_retry_error")
    @classmethod
    def enforce_client_reraise_from_retry_error_false(cls, value: bool) -> bool:
        """Enforce the False setting for client_reraise_from_retry_error"""
        if value:
            log.debug(
                "Forcing config value `client_reraise_from_retry_error` to False, as"
                + " that is the only supported value for this application."
            )
        return False


CONFIG = Config()
