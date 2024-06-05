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

"""Defines dataclasses for holding business-logic data"""

from pydantic import BaseModel


class InboundEnvelopeQuery(BaseModel):
    """Request object containing first file part and a public key."""

    file_part: str
    public_key: str


class InboundEnvelopeContent(BaseModel):
    """
    Contains file encryption/decryption secret extracted from file envelope, the ID
    generated for this secret and the file content offset, i.e. the location of the
    encrypted file content within the file.
    """

    submitter_secret: str
    new_secret: str
    secret_id: str
    offset: int


class OutboundEnvelopeContent(BaseModel):
    """
    Contains the header envelope, which contains the file secret encrypted with the
    client's public key and the server's private key
    """

    content: str
