# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

from os import path

import pytest
import typer

from ghga_connector.cli import (
    ApiNotReachable,
    DirectoryNotExist,
    MaxWaitTimeExceeded,
    download,
    upload,
)
from ghga_connector.core import (
    BadResponseCodeError,
    RequestFailedError,
    confirm_api_call,
)

from ..fixtures.mock_api.testcontainer import MockAPIContainer
from ..fixtures.utils import BASE_DIR

EXAMPLE_FOLDER = path.join(BASE_DIR.parent.parent.resolve(), "example_data")


@pytest.mark.parametrize(
    "bad_url,file_id,output_dir,max_wait_time,expected_exception",
    [
        (True, "1", EXAMPLE_FOLDER, "60", ApiNotReachable),
        (False, "1", EXAMPLE_FOLDER, "60", None),
        (False, "2", EXAMPLE_FOLDER, "60", BadResponseCodeError),
        (False, "10s", EXAMPLE_FOLDER, "60", MaxWaitTimeExceeded),
        (False, "1", "/this_path/", "60", DirectoryNotExist),
    ],
)
def test_download(bad_url, file_id, output_dir, max_wait_time, expected_exception):

    """Test the download of a file, expects Abort, if the file was not found"""
    with MockAPIContainer() as api:
        api_url = "http://bad_url" if bad_url else api.get_connection_url()

        try:
            download(
                api_url=api_url,
                file_id=file_id,
                output_dir=output_dir,
                max_wait_time=int(max_wait_time),
            )
            assert expected_exception is None
        except Exception as exception:
            assert isinstance(exception, expected_exception)


@pytest.mark.parametrize(
    "bad_url,file_id,file_path,expected_exception",
    [
        (
            True,
            "1",
            EXAMPLE_FOLDER,
            typer.Abort,
        ),
        (False, "1", path.join(EXAMPLE_FOLDER, "file1.test"), None),
        (False, "2", path.join(EXAMPLE_FOLDER, "file2.test"), typer.Abort),
        (
            False,
            "1",
            "/this_path/does_not_exist.test",
            typer.Abort,
        ),
    ],
)
def test_upload(bad_url, file_id, file_path, expected_exception):

    """Test the upload of a file, expects Abort, if the file was not found"""
    with MockAPIContainer() as api:
        api_url = "http://bad_url" if bad_url else api.get_connection_url()

        try:
            upload(api_url, file_id, file_path)
            assert expected_exception is None
        except Exception as exception:
            assert isinstance(exception, expected_exception)


@pytest.mark.parametrize(
    "bad_url,file_id,expected_exception",
    [
        (False, "1", None),
        (False, "2", BadResponseCodeError),
        (True, "1", RequestFailedError),
    ],
)
def test_confirm_api_call(bad_url, file_id, expected_exception):
    """
    Test the confirm_api_call function
    """
    with MockAPIContainer() as api:
        api_url = "http://bad_url" if bad_url else api.get_connection_url()

        try:
            confirm_api_call(api_url=api_url, file_id=file_id)
            assert expected_exception is None
        except Exception as exception:
            assert isinstance(exception, expected_exception)
