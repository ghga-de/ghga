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

"""
This sub-package contains the main business functionality of this service.
It should not contain any service API-related code.
"""

from .api_calls import (  # noqa: F401
    UploadStatus,
    await_download_url,
    download_api_call,
    get_pending_uploads,
    initiate_multipart_upload,
    patch_multipart_upload,
    start_multipart_upload,
    upload_part,
)
from .exceptions import (  # noqa: F401
    BadResponseCodeError,
    CantCancelUploadError,
    MaxRetriesReached,
    MaxWaitTimeExceeded,
    NoS3AccessMethod,
    NoUploadPossibleError,
    RequestFailedError,
)
from .file_operations import download_file_part, upload_file_part  # noqa: F401
from .main import check_url  # noqa: F401
