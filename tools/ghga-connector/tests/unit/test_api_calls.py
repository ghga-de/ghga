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

"""Tests for API Calls"""


import pytest

from ghga_connector.core import (
    BadResponseCodeError,
    RequestFailedError,
    UploadStatus,
    get_pending_uploads,
    patch_multipart_upload,
)

from ..fixtures.mock_api.testcontainer import MockAPIContainer


@pytest.mark.parametrize(
    "bad_url,file_id,expected_exception,expect_none",
    [
        (False, "pending", None, False),
        (False, "uploaded", None, True),
        (False, "confirmed", BadResponseCodeError, False),
        (True, "uploaded", RequestFailedError, False),
    ],
)
def test_get_pending_uploads(
    bad_url,
    file_id,
    expected_exception,
    expect_none,
):
    """
    Test the patch_multipart_upload function
    """
    with MockAPIContainer() as api:
        api_url = "http://bad_url" if bad_url else api.get_connection_url()

        try:
            response = get_pending_uploads(
                api_url=api_url,
                file_id=file_id,
            )
            assert expected_exception is None
            if expect_none:
                assert response is None
            elif response is not None:
                assert response[0]["upload_id"] == UploadStatus.PENDING
        except Exception as exception:
            assert isinstance(exception, expected_exception)


@pytest.mark.parametrize(
    "bad_url,upload_id,upload_status,expected_exception",
    [
        (False, "pending", UploadStatus.UPLOADED, None),
        (False, "uploaded", UploadStatus.CANCELLED, None),
        (False, "pending", UploadStatus.CANCELLED, BadResponseCodeError),
        (False, "uploadable", UploadStatus.UPLOADED, BadResponseCodeError),
        (True, "uploaded", UploadStatus.UPLOADED, RequestFailedError),
    ],
)
def test_patch_multipart_upload(
    bad_url,
    upload_id,
    upload_status,
    expected_exception,
):
    """
    Test the patch_multipart_upload function
    """
    with MockAPIContainer() as api:
        api_url = "http://bad_url" if bad_url else api.get_connection_url()

        try:
            patch_multipart_upload(
                api_url=api_url,
                upload_id=upload_id,
                upload_status=upload_status,
            )
            assert expected_exception is None
        except Exception as exception:
            assert isinstance(exception, expected_exception)
