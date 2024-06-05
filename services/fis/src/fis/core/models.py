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
"""Models for internal representation"""

from pydantic import BaseModel


class EncryptedPayload(BaseModel):
    """Generic model for an encrypted payload.

    Can correspond to current/legacy upload metadata or a file secret.
    """

    payload: str


class UploadMetadataBase(BaseModel):
    """BaseModel for common parts of different variants of the decrypted payload model
    representing the S3 upload script output
    """

    file_id: str
    object_id: str
    part_size: int
    unencrypted_size: int
    encrypted_size: int
    unencrypted_checksum: str
    encrypted_md5_checksums: list[str]
    encrypted_sha256_checksums: list[str]


class LegacyUploadMetadata(UploadMetadataBase):
    """Legacy model including file encryption/decryption secret"""

    file_secret: str


class UploadMetadata(UploadMetadataBase):
    """Current model including a secret ID that can be used to retrieve a stored secret
    in place of the actual secret.
    """

    secret_id: str
