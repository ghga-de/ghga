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

"""Config Parameter Modeling and Parsing."""

from re import split
from typing import Self

from ghga_service_commons.api import ApiConfigBase
from ghga_service_commons.utils.multinode_storage import S3ObjectStoragesConfig
from hexkit.config import config_from_yaml
from hexkit.log import LoggingConfig
from hexkit.providers.akafka import KafkaConfig
from pydantic import Field, SecretStr, field_validator, model_validator

from sms.core.secrets_handler import VaultConfig

SERVICE_NAME: str = "sms"


class SmsConfig(VaultConfig):
    """Configuration specific to the SMS."""

    token_hashes: list[str] = Field(
        default=...,
        description="List of token hashes corresponding to the tokens that can be used "
        + "to authenticate calls to this service. Hashes are made with SHA-256.",
        examples=["7ad83b6b9183c91674eec897935bc154ba9ff9704f8be0840e77f476b5062b6e"],
    )
    db_prefix: str = Field(
        default=...,
        description="Prefix to add to all database names used in the SMS.",
        examples=["testing-branch-name-"],
    )
    allow_empty_prefix: bool = Field(
        default=False,
        description="Only set to True for local testing. If False, `db_prefix` cannot be"
        + " empty. This is to prevent accidental deletion of others' data in shared"
        + " environments, i.e. staging.",
        examples=[True, False],
    )
    db_permissions: list[str] = Field(
        default=[],
        description=(
            "List of permissions that can be granted on a collection. Use * to signify"
            + " 'all'. The format is '<db_name>.<collection_name>:<permissions>', e.g."
            + " 'db1.collection1.crud'. The permissions are 'r' for read and 'w' for"
            + " write. '*' can be used to mean both read and write (or 'rw')."
            + " Deletion is a write operation. If db_permissions are not set, no"
            + " operations are allowed on any database or collection."
        ),
        examples=[
            "db1.coll1:r",
            "db1.coll1:w",
            "db1.coll1:rw",
            "db1.coll1:*",
            "db2.*:r",
            "db3.*:*",
            "*.*:r",
            "*.*:*",
        ],
    )
    db_connection_str: SecretStr = Field(
        default=...,
        examples=["mongodb://localhost:27017"],
        description=(
            "MongoDB connection string. Might include credentials."
            + " For more information see:"
            + " https://naiveskill.com/mongodb-connection-string/"
        ),
    )

    @field_validator("db_permissions")
    @classmethod
    def validate_permissions(cls, value) -> list[str] | None:
        """Validate the permissions to make sure only 'r', 'w', 'rw', and '*' are used.

        Rules are normalized by unpacking '*' into 'rw'.
        """
        if value is None:
            return value

        normalized_rules: list[str] = []
        for permission in value:
            db_name, collection, ops = split(r"\.(.*?):", permission)
            if not (db_name and collection and ops):
                raise ValueError(
                    f"Invalid permission '{permission}'."
                    + " Must have the format <db>.<collection>:<permissions>'."
                )
            ops = "rw" if ops == "*" else ops
            if ops not in ("r", "w", "rw"):
                raise ValueError(
                    f"Invalid permission '{ops}' in '{permission}'."
                    + " Only 'r', 'w', 'rw', and '*' are allowed."
                )
            normalized_rules.append(f"{db_name}.{collection}:{ops}")
        return normalized_rules

    @model_validator(mode="after")
    def validate_prefix(self) -> Self:
        """Make sure `db_prefix` and `allow_empty_prefix` are compatible."""
        if not self.db_prefix and not self.allow_empty_prefix:
            raise ValueError(
                "'db_prefix' cannot be blank if 'allow_empty_prefix' is False!"
            )
        return self


@config_from_yaml(prefix=SERVICE_NAME)
class Config(
    ApiConfigBase,
    LoggingConfig,
    SmsConfig,
    S3ObjectStoragesConfig,
    KafkaConfig,
):
    """Config parameters and their defaults."""

    service_name: str = Field(
        default=SERVICE_NAME, description="Short name of this service"
    )
