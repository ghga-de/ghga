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

import os
import pathlib
from contextlib import nullcontext
from filecmp import cmp
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest
from ghga_service_chassis_lib.utils import big_temp_file

from ghga_connector.cli import download, upload
from ghga_connector.core import exceptions
from ghga_connector.core.constants import DEFAULT_PART_SIZE
from tests.fixtures import state
from tests.fixtures.config import get_test_config
from tests.fixtures.mock_api.testcontainer import MockAPIContainer
from tests.fixtures.s3 import S3Fixture, get_big_s3_object, s3_fixture  # noqa: F401
from tests.fixtures.utils import BASE_DIR

PUBLIC_KEY_FILE = BASE_DIR / "keypair/key.pub"


@pytest.mark.parametrize(
    "file_size,part_size",
    [
        (6 * 1024 * 1024, 5 * 1024 * 1024),
        (12 * 1024 * 1024, 5 * 1024 * 1024),
        (1 * 1024 * 1024, DEFAULT_PART_SIZE),
        (20 * 1024 * 1024, DEFAULT_PART_SIZE),
    ],
)
def test_multipart_download(
    file_size: int,
    part_size: int,
    s3_fixture: S3Fixture,  # noqa F811
    tmp_path: pathlib.Path,
):
    """Test the multipart download of a file"""
    big_object = get_big_s3_object(s3_fixture, object_size=file_size)

    # right now the desired file size is only
    # approximately met by the provided big file:
    file_size_ = len(big_object.content)

    # get s3 download url
    download_url = s3_fixture.storage.get_object_download_url(
        bucket_id=big_object.bucket_id,
        object_id=big_object.object_id,
        expires_after=180,
    )
    with MockAPIContainer(
        s3_download_url=download_url,
        s3_download_file_size=file_size_,
    ) as api:
        api_url = api.get_connection_url()
        with patch(
            "ghga_connector.cli.config",
            get_test_config(download_api=api_url, part_size=part_size),
        ):
            download(
                file_id=big_object.object_id,
                output_dir=tmp_path,
            )
        with open(tmp_path / big_object.object_id, "rb") as file:
            observed_content = file.read()

        assert observed_content == big_object.content


@pytest.mark.parametrize(
    "bad_url,bad_outdir,file_name,expected_exception",
    [
        (True, False, "file_downloadable", exceptions.ApiNotReachableError),
        (False, False, "file_downloadable", None),
        (
            False,
            False,
            "file_not_downloadable",
            exceptions.BadResponseCodeError,
        ),
        (False, False, "file_retry", exceptions.MaxWaitTimeExceededError),
        (False, True, "file_downloadable", exceptions.DirectoryDoesNotExistError),
    ],
)
def test_download(
    bad_url: bool,
    bad_outdir: bool,
    file_name: str,
    expected_exception: type[Optional[Exception]],
    s3_fixture: S3Fixture,  # noqa: F811
    tmp_path: pathlib.Path,
):
    """Test the download of a file"""

    output_dir = Path("/non/existing/path") if bad_outdir else tmp_path

    file = state.FILES[file_name]

    if file.populate_storage:

        download_url = s3_fixture.storage.get_object_download_url(
            bucket_id=file.grouping_label,
            object_id=file.file_id,
            expires_after=60,
        )

    else:
        download_url = ""

    with MockAPIContainer(
        s3_download_url=download_url,
        s3_download_file_size=os.path.getsize(file.file_path),
    ) as api:
        api_url = "http://bad_url" if bad_url else api.get_connection_url()

        with patch(
            "ghga_connector.cli.config",
            get_test_config(download_api=api_url),
        ):
            with pytest.raises(  # type: ignore
                expected_exception
            ) if expected_exception else nullcontext():
                download(file_id=file.file_id, output_dir=output_dir)

        if not expected_exception:
            assert cmp(output_dir / file.file_id, file.file_path)


@pytest.mark.parametrize(
    "bad_url,file_name,expected_exception",
    [
        (True, "file_uploadable", exceptions.ApiNotReachableError),
        (False, "file_uploadable", None),
        (False, "file_not_uploadable", exceptions.FileNotRegisteredError),
        (False, "file_with_bad_path", exceptions.FileDoesNotExistError),
    ],
)
def test_upload(
    bad_url: bool,
    file_name: str,
    expected_exception: type[Optional[Exception]],
    s3_fixture: S3Fixture,  # noqa F811
):
    """Test the upload of a file, expects Abort, if the file was not found"""

    uploadable_file = state.FILES[file_name]

    # initiate upload
    upload_id = s3_fixture.storage.init_multipart_upload(
        bucket_id=uploadable_file.grouping_label,
        object_id=uploadable_file.file_id,
    )

    upload_url = s3_fixture.storage.get_part_upload_url(
        bucket_id=uploadable_file.grouping_label,
        object_id=uploadable_file.file_id,
        upload_id=upload_id,
        part_number=1,
    )

    with MockAPIContainer(s3_upload_url_1=upload_url) as api:
        api_url = "http://bad_url" if bad_url else api.get_connection_url()

        with patch("ghga_connector.cli.config", get_test_config(upload_api=api_url)):
            with pytest.raises(  # type: ignore
                expected_exception
            ) if expected_exception else nullcontext():
                upload(
                    file_id=uploadable_file.file_id,
                    file_path=uploadable_file.file_path.resolve(),
                    pubkey_path=Path(PUBLIC_KEY_FILE),
                )

                s3_fixture.storage.complete_multipart_upload(
                    upload_id=upload_id,
                    bucket_id=uploadable_file.grouping_label,
                    object_id=uploadable_file.file_id,
                )

                assert s3_fixture.storage.does_object_exist(
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
def test_multipart_upload(
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
    upload_id = s3_fixture.storage.init_multipart_upload(
        bucket_id=bucket_id,
        object_id=file_id,
    )

    # create presigned url for upload part 1
    upload_url_1 = s3_fixture.storage.get_part_upload_url(
        upload_id=upload_id,
        bucket_id=bucket_id,
        object_id=file_id,
        part_number=1,
    )

    # create presigned url for upload part 2
    upload_url_2 = s3_fixture.storage.get_part_upload_url(
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
                "ghga_connector.cli.config",
                get_test_config(upload_api=api_url),
            ):
                upload(
                    file_id=file_id,
                    file_path=Path(file.name),
                    pubkey_path=Path(PUBLIC_KEY_FILE),
                )

        # confirm upload
        s3_fixture.storage.complete_multipart_upload(
            upload_id=upload_id,
            bucket_id=bucket_id,
            object_id=file_id,
            anticipated_part_quantity=anticipated_part_quantity,
            anticipated_part_size=anticipated_part_size,
        )
        assert s3_fixture.storage.does_object_exist(
            bucket_id=bucket_id,
            object_id=file_id,
        )
