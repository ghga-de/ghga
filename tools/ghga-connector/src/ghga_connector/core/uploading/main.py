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
"""Contains general logic that needs to be exposed to higher level core functionality"""

from pathlib import Path

from ghga_connector.core import exceptions
from ghga_connector.core.crypt import Crypt4GHEncryptor

from .abstract_uploader import UploaderBase
from .uploader import ChunkedUploader


async def run_upload(  # noqa: PLR0913
    file_id: str,
    file_path: Path,
    my_private_key_path: Path,
    part_size: int,
    server_public_key: str,
    uploader: UploaderBase,
):
    """Initialize client and uploader and delegate to function performing the actual upload"""
    encryptor = Crypt4GHEncryptor(
        part_size=part_size,
        private_key_path=my_private_key_path,
        server_public_key=server_public_key,
    )
    chunked_uploader = ChunkedUploader(
        encryptor=encryptor,
        file_path=file_path,
        file_id=file_id,
        part_size=part_size,
        uploader=uploader,
    )

    try:
        await uploader.start_multipart_upload()
    except (
        exceptions.BadResponseCodeError,
        exceptions.FileNotRegisteredError,
        exceptions.NoUploadPossibleError,
        exceptions.RequestFailedError,
        exceptions.UploadNotRegisteredError,
        exceptions.NoUploadAccessError,
    ) as error:
        raise exceptions.StartUploadError() from error

    try:
        await chunked_uploader.encrypt_and_upload()
    except exceptions.ConnectionFailedError as error:
        raise error

    try:
        await uploader.finish_multipart_upload()
    except exceptions.BadResponseCodeError as error:
        raise exceptions.FinalizeUploadError(
            cause="The request to confirm the upload was invalid."
        ) from error
    except exceptions.RequestFailedError as error:
        raise exceptions.FinalizeUploadError(
            cause="Confirming the upload failed."
        ) from error
