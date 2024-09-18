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

"""This file contains all api calls related to uploading files"""

import base64
import json
import math
from collections.abc import Iterator
from pathlib import Path

import crypt4gh.keys
import crypt4gh.lib
import httpx

from ghga_connector.constants import MAX_PART_NUMBER
from ghga_connector.core import ResponseExceptionTranslator, exceptions
from ghga_connector.core.crypt import Encryptor

from .abstract_uploader import UploaderBase
from .structs import UploadStatus


class Uploader(UploaderBase):
    """
    Class bundling functionality calling Upload Controller Service to initiate and
    manage an ongoing upload
    """

    def __init__(
        self,
        *,
        api_url: str,
        client: httpx.AsyncClient,
        file_id: str,
        public_key_path: Path,
    ) -> None:
        self._part_size = 0
        self._upload_id = ""
        self._api_url = api_url
        self._client = client
        self._file_id = file_id
        self._public_key_path = public_key_path

    async def start_multipart_upload(self):
        """Start multipart upload"""
        try:
            await self._initiate_multipart_upload()

        except exceptions.NoUploadPossibleError as error:
            file_metadata = await self.get_file_metadata()
            upload_id = file_metadata["current_upload_id"]
            if upload_id is None:
                raise error

            await self.patch_multipart_upload(
                upload_status=UploadStatus.CANCELLED,
            )

            await self._initiate_multipart_upload()

        except Exception as error:
            raise error

    async def finish_multipart_upload(self):
        """Complete or clean up multipart upload"""
        await self.patch_multipart_upload(upload_status=UploadStatus.UPLOADED)

    async def _initiate_multipart_upload(self) -> None:
        """
        Perform a RESTful API call to initiate a multipart upload
        Returns an upload id and a part size
        """
        # build url and headers
        url = f"{self._api_url}/uploads"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        public_key = base64.b64encode(
            crypt4gh.keys.get_public_key(self._public_key_path)
        ).decode()

        post_data = {"file_id": self._file_id, "public_key": public_key}
        serialized_data = json.dumps(post_data)

        # Make function call to get upload url
        try:
            response = await self._client.post(
                url=url, headers=headers, content=serialized_data
            )
        except httpx.RequestError as request_error:
            exceptions.raise_if_connection_failed(request_error=request_error, url=url)
            raise exceptions.RequestFailedError(url=url) from request_error

        status_code = response.status_code
        if status_code != 200:
            spec = {
                400: {
                    "existingActiveUpload": lambda: exceptions.NoUploadPossibleError(
                        file_id=self._file_id
                    ),
                    "fileNotRegistered": lambda: exceptions.FileNotRegisteredError(
                        file_id=self._file_id
                    ),
                },
                403: {
                    "noFileAccess": lambda: exceptions.NoFileAccessError(
                        file_id=self._file_id
                    )
                },
            }
            ResponseExceptionTranslator(spec=spec).handle(response=response)
            raise exceptions.BadResponseCodeError(url=url, response_code=status_code)

        response_body = response.json()

        self._part_size = int(response_body["part_size"])
        self._upload_id = response_body["upload_id"]

    async def get_file_metadata(self) -> dict[str, str]:
        """Get all file metadata"""
        # build url and headers
        url = f"{self._api_url}/files/{self._file_id}"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        try:
            response = await self._client.get(url=url, headers=headers)
        except httpx.RequestError as request_error:
            exceptions.raise_if_connection_failed(request_error=request_error, url=url)
            raise exceptions.RequestFailedError(url=url) from request_error

        status_code = response.status_code
        if status_code != 200:
            spec = {
                403: {
                    "noFileAccess": lambda: exceptions.NoFileAccessError(
                        file_id=self._file_id
                    )
                },
                404: {
                    "fileNotRegistered": lambda: exceptions.FileNotRegisteredError(
                        file_id=self._file_id
                    )
                },
            }
            ResponseExceptionTranslator(spec=spec).handle(response=response)
            raise exceptions.BadResponseCodeError(url=url, response_code=status_code)

        file_metadata = response.json()

        return file_metadata

    async def get_part_upload_url(self, *, part_no: int) -> str:
        """Get a presigned url to upload a specific part"""
        if not self._upload_id:
            raise exceptions.UploadIdUnsetError()

        # build url and headers
        url = f"{self._api_url}/uploads/{self._upload_id}/parts/{part_no}/signed_urls"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        # Make function call to get upload url
        try:
            response = await self._client.post(url=url, headers=headers)
        except httpx.RequestError as request_error:
            exceptions.raise_if_connection_failed(request_error=request_error, url=url)
            raise exceptions.RequestFailedError(url=url) from request_error

        status_code = response.status_code
        if status_code != 200:
            spec = {
                403: {
                    "noFileAccess": lambda: exceptions.NoUploadAccessError(
                        upload_id=self._upload_id
                    )
                },
                404: {
                    "noSuchUpload": lambda: exceptions.UploadNotRegisteredError(
                        upload_id=self._upload_id
                    )
                },
            }
            ResponseExceptionTranslator(spec=spec).handle(response=response)
            raise exceptions.BadResponseCodeError(url=url, response_code=status_code)

        response_body = response.json()
        presigned_url = response_body["url"]

        return presigned_url

    def get_part_upload_urls(
        self,
        *,
        from_part: int = 1,
        get_url_func=get_part_upload_url,
    ) -> Iterator[str]:
        """
        Return an iterator for a specific multipart upload to lazily iterate through
        file parts and obtain the corresponding upload urls.

        By default this starts with the first part but you may also start from a
        specific part using the `from_part` argument.

        Please note: the upload must already have been initiated.
        """
        if not self._upload_id:
            raise exceptions.UploadIdUnsetError()

        for part_no in range(from_part, MAX_PART_NUMBER + 1):
            yield get_url_func(
                api_url=self._api_url, upload_id=self._upload_id, part_no=part_no
            )

        raise exceptions.MaxPartNoExceededError()

    async def get_upload_info(self) -> dict[str, str]:
        """Get details on a specific upload"""
        if not self._upload_id:
            raise exceptions.UploadIdUnsetError()

        # build url and headers
        url = f"{self._api_url}/uploads/{self._upload_id}"
        headers = {"Accept": "*/*", "Content-Type": "application/json"}

        try:
            response = await self._client.get(url=url, headers=headers)
        except httpx.RequestError as request_error:
            exceptions.raise_if_connection_failed(request_error=request_error, url=url)
            raise exceptions.RequestFailedError(url=url) from request_error

        status_code = response.status_code
        if status_code != 200:
            spec = {
                403: {
                    "noFileAccess": lambda: exceptions.NoUploadAccessError(
                        upload_id=self._upload_id
                    )
                },
                404: {
                    "noSuchUpload": lambda: exceptions.UploadNotRegisteredError(
                        upload_id=self._upload_id
                    )
                },
            }
            ResponseExceptionTranslator(spec=spec).handle(response=response)
            raise exceptions.BadResponseCodeError(url=url, response_code=status_code)

        return response.json()

    async def patch_multipart_upload(self, *, upload_status: UploadStatus) -> None:
        """
        Set the status of a specific upload attempt.
        The API accepts "uploaded" or "accepted",
        if the upload_id is currently set to "pending"
        """
        if not self._upload_id:
            raise exceptions.UploadIdUnsetError()

        # build url and headers
        url = f"{self._api_url}/uploads/{self._upload_id}"
        headers = {"Accept": "*/*", "Content-Type": "application/json"}
        post_data = {"status": upload_status}
        serialized_data = json.dumps(post_data)

        try:
            response = await self._client.patch(
                url=url, headers=headers, content=serialized_data
            )
        except httpx.RequestError as request_error:
            exceptions.raise_if_connection_failed(request_error=request_error, url=url)
            raise exceptions.RequestFailedError(url=url) from request_error

        status_code = response.status_code
        if status_code != 204:
            spec = {
                400: {
                    "uploadNotPending": lambda: exceptions.CantChangeUploadStatusError(
                        upload_id=self._upload_id, upload_status=upload_status
                    ),
                    "uploadStatusChange": lambda: exceptions.CantChangeUploadStatusError(
                        upload_id=self._upload_id, upload_status=upload_status
                    ),
                },
                403: {
                    "noFileAccess": lambda: exceptions.NoUploadAccessError(
                        upload_id=self._upload_id
                    )
                },
                404: {
                    "noSuchUpload": lambda: exceptions.UploadNotRegisteredError(
                        upload_id=self._upload_id
                    )
                },
            }
            ResponseExceptionTranslator(spec=spec).handle(response=response)
            raise exceptions.BadResponseCodeError(url=url, response_code=status_code)

    async def upload_file_part(self, *, presigned_url: str, part: bytes) -> None:
        """Upload File"""
        try:
            response = await self._client.put(presigned_url, content=part)
        except httpx.RequestError as request_error:
            exceptions.raise_if_connection_failed(
                request_error=request_error, url=presigned_url
            )
            raise exceptions.RequestFailedError(url=presigned_url) from request_error

        status_code = response.status_code
        if status_code == 200:
            return

        raise exceptions.BadResponseCodeError(
            url=presigned_url, response_code=status_code
        )


class ChunkedUploader:
    """Handler class dealing with upload functionality"""

    def __init__(
        self,
        *,
        encryptor: Encryptor,
        file_id: str,
        file_path: Path,
        part_size: int,
        uploader: UploaderBase,
    ) -> None:
        self._encrypted_file_size = 0
        self._encryptor = encryptor
        self._file_id = file_id
        self._input_path = file_path
        self._part_size = part_size
        self._unencrypted_file_size = file_path.stat().st_size
        self._uploader = uploader

    async def encrypt_and_upload(self):
        """Delegate encryption and perform multipart upload"""
        # compute encrypted_file_size
        num_segments = math.ceil(
            self._unencrypted_file_size / crypt4gh.lib.SEGMENT_SIZE
        )
        expected_encrypted_size = (
            self._unencrypted_file_size + num_segments * crypt4gh.lib.CIPHER_DIFF
        )

        with self._input_path.open("rb") as file:
            for part_number, part in enumerate(
                self._encryptor.process_file(file=file), start=1
            ):
                upload_url = await self._uploader.get_part_upload_url(
                    part_no=part_number
                )
                await self._uploader.upload_file_part(
                    presigned_url=upload_url, part=part
                )
            encrypted_file_size = self._encryptor.get_encrypted_size()
            if expected_encrypted_size != encrypted_file_size:
                raise exceptions.EncryptedSizeMismatch(
                    actual_encrypted_size=encrypted_file_size,
                    expected_encrypted_size=expected_encrypted_size,
                )
