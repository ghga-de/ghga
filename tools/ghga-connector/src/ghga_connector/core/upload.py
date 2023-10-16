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
"""Module dealing with intermediate upload path abstractions"""

import math
from pathlib import Path

import crypt4gh.lib

from ghga_connector.core import exceptions
from ghga_connector.core.api_calls import Uploader
from ghga_connector.core.client import async_client
from ghga_connector.core.file_operations import Crypt4GHEncryptor
from ghga_connector.core.message_display import AbstractMessageDisplay


class ChunkedUploader:
    """Handler class dealing with upload functionality"""

    def __init__(
        self, encryptor: Crypt4GHEncryptor, file_path: Path, uploader: Uploader
    ) -> None:
        self.encrypted_file_size = 0
        self.encryptor = encryptor
        self.file_id = uploader._file_id
        self.input_path = file_path
        self.part_size = uploader.part_size
        self.unencrypted_file_size = file_path.stat().st_size
        self.uploader = uploader

    async def encrypt_and_upload(self):
        """Delegate encryption and perform multipart upload"""
        # compute encrypted_file_size
        num_segments = math.ceil(self.unencrypted_file_size / crypt4gh.lib.SEGMENT_SIZE)
        expected_encrypted_size = (
            self.unencrypted_file_size + num_segments * crypt4gh.lib.CIPHER_DIFF
        )

        with self.input_path.open("rb") as file:
            for part_number, part in enumerate(
                self.encryptor.process_file(file=file), start=1
            ):
                upload_url = await self.uploader.get_part_upload_url(
                    part_no=part_number
                )
                await self.uploader.upload_file_part(
                    presigned_url=upload_url, part=part
                )
            if expected_encrypted_size != self.encryptor.encrypted_file_size:
                raise exceptions.EncryptedSizeMismatch(
                    actual_encrypted_size=self.encryptor.encrypted_file_size,
                    expected_encrypted_size=expected_encrypted_size,
                )


async def run_upload(  # noqa: PLR0913
    api_url: str,
    file_id: str,
    file_path: Path,
    message_display: AbstractMessageDisplay,
    private_key_path: Path,
    public_key_path: Path,
    server_public_key: str,
):
    """
    Initialize httpx.client and Uploader and delegate to function peforming the actual
    upload
    """
    async with async_client() as client:
        uploader = Uploader(
            api_url=api_url,
            client=client,
            file_id=file_id,
            public_key_path=public_key_path,
        )

        try:
            await uploader.start_multipart_upload()
        except (
            exceptions.BadResponseCodeError,
            exceptions.FileNotRegisteredError,
            exceptions.NoUploadPossibleError,
            exceptions.UploadNotRegisteredError,
            exceptions.UserHasNoUploadAccessError,
        ) as error:
            raise error
        except exceptions.CantChangeUploadStatusError as error:
            message_display.failure(
                f"The file with id '{file_id}' was already uploaded."
            )
            raise error
        except exceptions.RequestFailedError as error:
            message_display.failure(
                "The request to start a multipart upload has failed."
            )
            raise error

        try:
            await execute_upload(
                uploader=uploader,
                file_path=file_path,
                private_key_path=private_key_path,
                server_public_key=server_public_key,
            )
        except exceptions.ConnectionFailedError as error:
            message_display.failure("The upload failed too many times and was aborted.")
            raise error

        try:
            await uploader.finish_multipart_upload()
        except exceptions.BadResponseCodeError as error:
            message_display.failure(
                f"The request to confirm the upload with id '{uploader.upload_id}' was invalid."
            )
            raise error
        except exceptions.RequestFailedError as error:
            message_display.failure(
                f"Confirming the upload with id '{uploader.upload_id}' failed."
            )
            raise error


async def execute_upload(
    uploader: Uploader, file_path: Path, private_key_path: Path, server_public_key: str
):
    """
    Create encryptor and chunked_uploader instances for a given uploaded and call the
    method performing
    """
    encryptor = Crypt4GHEncryptor(
        part_size=uploader.part_size,
        private_key_path=private_key_path,
        server_public_key=server_public_key,
    )
    chunked_uploader = ChunkedUploader(
        encryptor=encryptor, file_path=file_path, uploader=uploader
    )
    await chunked_uploader.encrypt_and_upload()
