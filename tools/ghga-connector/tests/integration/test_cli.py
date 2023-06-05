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

"""Tests for the up- and download functions of the cli"""

import base64
import os
import pathlib
from contextlib import nullcontext
from filecmp import cmp
from pathlib import Path
from typing import Optional
from unittest.mock import Mock, patch

import crypt4gh.keys
import pytest
from ghga_service_commons.utils.temp_files import big_temp_file

from ghga_connector.cli import download, upload
from ghga_connector.core import exceptions
from ghga_connector.core.constants import DEFAULT_PART_SIZE
from ghga_connector.core.file_operations import Crypt4GHEncryptor
from tests.fixtures import state
from tests.fixtures.config import get_test_config
from tests.fixtures.mock_api.testcontainer import MockAPIContainer
from tests.fixtures.s3 import S3Fixture, get_big_s3_object, s3_fixture  # noqa: F401
from tests.fixtures.utils import PRIVATE_KEY_FILE, PUBLIC_KEY_FILE, mock_wps_token


@pytest.mark.parametrize(
    "file_size,part_size",
    [
        (6 * 1024 * 1024, 5 * 1024 * 1024),
        (12 * 1024 * 1024, 5 * 1024 * 1024),
        (20 * 1024 * 1024, 1 * 1024 * 1024),
        (20 * 1024 * 1024, 64 * 1024),
        (1 * 1024 * 1024, DEFAULT_PART_SIZE),
        (20 * 1024 * 1024, DEFAULT_PART_SIZE),
    ],
)
@pytest.mark.asyncio
async def test_multipart_download(
    file_size: int,
    part_size: int,
    s3_fixture: S3Fixture,  # noqa F811
    tmp_path: pathlib.Path,
    monkeypatch,
):
    """Test the multipart download of a file"""
    big_object = await get_big_s3_object(s3_fixture, object_size=file_size)

    # The download function will ask the user for input.
    monkeypatch.setattr("ghga_connector.core.main.get_wps_token", mock_wps_token)
    monkeypatch.setattr(
        "ghga_connector.core.api_calls.work_package.WorkPackageAccessor.get_package_files",
        Mock(return_value=dict(zip([big_object.object_id], [""]))),
    )
    monkeypatch.setattr(
        "ghga_connector.core.api_calls.work_package._decrypt",
        lambda data, key: data,
    )

    # right now the desired file size is only
    # approximately met by the provided big file:
    file_size_ = len(big_object.content)

    # get s3 download url
    download_url = await s3_fixture.storage.get_object_download_url(
        bucket_id=big_object.bucket_id,
        object_id=big_object.object_id,
        expires_after=180,
    )

    fake_envelope = "Thisisafakeenvelope"

    with MockAPIContainer(
        s3_download_url=download_url,
        s3_download_file_size=file_size_,
        fake_envelope=fake_envelope,
    ) as api:
        api_url = api.get_connection_url()
        with patch(
            "ghga_connector.cli.CONFIG",
            get_test_config(
                download_api=api_url,
                part_size=part_size,
                wps_api_url=api.get_connection_url(),
            ),
        ):
            download(
                output_dir=tmp_path,
                submitter_pubkey_path=Path(PUBLIC_KEY_FILE),
                submitter_private_key_path=Path(PRIVATE_KEY_FILE),
            )

        big_file_content = str.encode(fake_envelope)
        big_file_content += big_object.content
        with open(tmp_path / f"{big_object.object_id}.c4gh", "rb") as file:
            observed_content = file.read()

        assert observed_content == big_file_content


@pytest.mark.parametrize(
    "bad_url,bad_outdir,file_name,expected_exception,proceed_on_missing",
    [
        (True, False, "file_downloadable", exceptions.ApiNotReachableError, True),
        (False, False, "file_downloadable", None, True),
        (False, False, "file_not_downloadable", None, True),
        (
            False,
            False,
            "file_not_downloadable",
            exceptions.AbortBatchProcessError,
            False,
        ),
        (False, False, "file_retry", exceptions.MaxWaitTimeExceededError, True),
        (False, True, "file_downloadable", exceptions.DirectoryDoesNotExistError, True),
        (
            False,
            False,
            "file_envelope_missing",
            exceptions.FileNotRegisteredError,
            True,
        ),
    ],
)
@pytest.mark.asyncio
async def test_download(
    bad_url: bool,
    bad_outdir: bool,
    file_name: str,
    expected_exception: type[Optional[Exception]],
    s3_fixture: S3Fixture,  # noqa: F811
    tmp_path: pathlib.Path,
    proceed_on_missing: bool,
    monkeypatch,
):
    """Test the download of a file"""
    output_dir = Path("/non/existing/path") if bad_outdir else tmp_path

    file = state.FILES[file_name]

    # The download function will ask the user for input.
    monkeypatch.setattr("ghga_connector.core.main.get_wps_token", mock_wps_token)
    monkeypatch.setattr(
        "ghga_connector.core.api_calls.work_package.WorkPackageAccessor.get_package_files",
        Mock(return_value=dict(zip([file.file_id], [""]))),
    )
    monkeypatch.setattr(
        "ghga_connector.core.api_calls.work_package._decrypt",
        lambda data, key: data,
    )

    if file.populate_storage:
        download_url = await s3_fixture.storage.get_object_download_url(
            bucket_id=file.grouping_label,
            object_id=file.file_id,
            expires_after=60,
        )

    else:
        download_url = ""

    fake_envelope = "Thisisafakeenvelope"

    with MockAPIContainer(
        s3_download_url=download_url,
        s3_download_file_size=os.path.getsize(file.file_path),
        fake_envelope=fake_envelope,
    ) as api:
        api_url = "http://bad_url" if bad_url else api.get_connection_url()

        with patch(
            "ghga_connector.cli.CONFIG",
            get_test_config(download_api=api_url, wps_api_url=api.get_connection_url()),
        ):
            # needed to mock user input
            with patch(
                "ghga_connector.core.batch_processing.CliInputHandler.get_input",
                return_value="yes" if proceed_on_missing else "no",
            ):
                if file_name == "file_not_downloadable":
                    # check both 403 scenarios
                    with patch(
                        "ghga_connector.core.api_calls.work_package._decrypt",
                        lambda data, key: "authfail_normal",
                    ):
                        with pytest.raises(
                            exceptions.UnauthorizedAPICallError,
                            match="This is not the token you're looking for.",
                        ):
                            download(
                                output_dir=output_dir,
                                submitter_pubkey_path=Path(PUBLIC_KEY_FILE),
                                submitter_private_key_path=Path(PRIVATE_KEY_FILE),
                            )
                    with patch(
                        "ghga_connector.core.api_calls.work_package._decrypt",
                        lambda data, key: "file_id_mismatch",
                    ):
                        with pytest.raises(
                            exceptions.UnauthorizedAPICallError,
                            match="Endpoint file ID did not match file ID announced in work order token.",
                        ):
                            download(
                                output_dir=output_dir,
                                submitter_pubkey_path=Path(PUBLIC_KEY_FILE),
                                submitter_private_key_path=Path(PRIVATE_KEY_FILE),
                            )
                else:
                    with pytest.raises(  # type: ignore
                        expected_exception
                    ) if expected_exception else nullcontext():
                        download(
                            output_dir=output_dir,
                            submitter_pubkey_path=Path(PUBLIC_KEY_FILE),
                            submitter_private_key_path=Path(PRIVATE_KEY_FILE),
                        )

        # BadResponseCode is no longer propagated and file at path does not exist
        if file_name == "file_not_downloadable":
            return

        tmp_file = tmp_path / "file_with_envelope"

        # Copy fake envelope into new temp file, then append the test file
        with tmp_file.open("wb") as file_write:
            with file.file_path.open("rb") as file_read:
                buffer = file_read.read()
                file_write.write(str.encode(fake_envelope))
                file_write.write(buffer)

        if not expected_exception:
            assert cmp(output_dir / f"{file.file_id}.c4gh", tmp_file)


@pytest.mark.parametrize(
    "bad_url,file_name,expected_exception",
    [
        (True, "file_uploadable", exceptions.ApiNotReachableError),
        (False, "file_uploadable", None),
        (False, "file_not_uploadable", exceptions.FileNotRegisteredError),
        (False, "file_with_bad_path", exceptions.FileDoesNotExistError),
        (False, "encrypted_file", exceptions.FileAlreadyEncryptedError),
    ],
)
@pytest.mark.asyncio
async def test_upload(
    bad_url: bool,
    file_name: str,
    expected_exception: type[Optional[Exception]],
    s3_fixture: S3Fixture,  # noqa F811
):
    """Test the upload of a file, expects Abort, if the file was not found"""
    uploadable_file = state.FILES[file_name]

    if file_name == "encrypted_file":
        # encrypt test file on the fly
        server_pubkey = base64.b64encode(
            crypt4gh.keys.get_public_key(PUBLIC_KEY_FILE)
        ).decode("utf-8")
        encryptor = Crypt4GHEncryptor(
            server_pubkey=server_pubkey, submitter_private_key_path=PRIVATE_KEY_FILE
        )
        encrypted_path = encryptor.encrypt_file(file_path=uploadable_file.file_path)

    # initiate upload
    upload_id = await s3_fixture.storage.init_multipart_upload(
        bucket_id=uploadable_file.grouping_label,
        object_id=uploadable_file.file_id,
    )

    upload_url = await s3_fixture.storage.get_part_upload_url(
        bucket_id=uploadable_file.grouping_label,
        object_id=uploadable_file.file_id,
        upload_id=upload_id,
        part_number=1,
    )

    with MockAPIContainer(s3_upload_url_1=upload_url) as api:
        api_url = "http://bad_url" if bad_url else api.get_connection_url()

        with patch("ghga_connector.cli.CONFIG", get_test_config(upload_api=api_url)):
            with pytest.raises(  # type: ignore
                expected_exception
            ) if expected_exception else nullcontext():
                if file_name == "encrypted_file":
                    upload(
                        file_id=uploadable_file.file_id,
                        file_path=Path(encrypted_path).resolve(),
                        submitter_pubkey_path=Path(PUBLIC_KEY_FILE),
                        submitter_private_key_path=Path(PRIVATE_KEY_FILE),
                    )
                else:
                    upload(
                        file_id=uploadable_file.file_id,
                        file_path=uploadable_file.file_path.resolve(),
                        submitter_pubkey_path=Path(PUBLIC_KEY_FILE),
                        submitter_private_key_path=Path(PRIVATE_KEY_FILE),
                    )

                await s3_fixture.storage.complete_multipart_upload(
                    upload_id=upload_id,
                    bucket_id=uploadable_file.grouping_label,
                    object_id=uploadable_file.file_id,
                )

                assert await s3_fixture.storage.does_object_exist(
                    bucket_id=uploadable_file.grouping_label,
                    object_id=uploadable_file.file_id,
                )


@pytest.mark.parametrize(
    "file_size,anticipated_part_size",
    [
        (6 * 1024 * 1024, 8),
        (20 * 1024 * 1024, 16),
    ],
)
@pytest.mark.asyncio
async def test_multipart_upload(
    file_size: int,
    anticipated_part_size: int,
    s3_fixture: S3Fixture,  # noqa F811
):
    """Test the upload of a file, expects Abort, if the file was not found"""
    bucket_id = s3_fixture.existing_buckets[0]
    file_id = "uploadable-" + str(anticipated_part_size)

    anticipated_part_size = anticipated_part_size * 1024 * 1024

    anticipated_part_quantity = file_size // anticipated_part_size

    if anticipated_part_quantity * anticipated_part_size < file_size:
        anticipated_part_quantity += 1

    # initiate upload
    upload_id = await s3_fixture.storage.init_multipart_upload(
        bucket_id=bucket_id,
        object_id=file_id,
    )

    # create presigned url for upload part 1
    upload_url_1 = await s3_fixture.storage.get_part_upload_url(
        upload_id=upload_id,
        bucket_id=bucket_id,
        object_id=file_id,
        part_number=1,
    )

    # create presigned url for upload part 2
    upload_url_2 = await s3_fixture.storage.get_part_upload_url(
        upload_id=upload_id,
        bucket_id=bucket_id,
        object_id=file_id,
        part_number=2,
    )

    with MockAPIContainer(
        s3_upload_url_1=upload_url_1,
        s3_upload_url_2=upload_url_2,
    ) as api:
        api_url = api.get_connection_url()

        # create big temp file
        with big_temp_file(file_size) as file:
            with patch(
                "ghga_connector.cli.CONFIG",
                get_test_config(upload_api=api_url),
            ):
                upload(
                    file_id=file_id,
                    file_path=Path(file.name),
                    submitter_pubkey_path=Path(PUBLIC_KEY_FILE),
                    submitter_private_key_path=Path(PRIVATE_KEY_FILE),
                )

        # confirm upload
        await s3_fixture.storage.complete_multipart_upload(
            upload_id=upload_id,
            bucket_id=bucket_id,
            object_id=file_id,
            anticipated_part_quantity=anticipated_part_quantity,
            anticipated_part_size=anticipated_part_size,
        )
        assert await s3_fixture.storage.does_object_exist(
            bucket_id=bucket_id,
            object_id=file_id,
        )
