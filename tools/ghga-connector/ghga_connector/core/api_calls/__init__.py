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

"""
This sub-package contains the api calls, this service makes for various purposes
"""

from .download import (  # noqa: F401
    await_download_url,
    get_download_url,
    get_download_urls,
    get_file_header_envelope,
)
from .upload import (  # noqa: F401
    UploadStatus,
    get_file_metadata,
    get_part_upload_url,
    get_part_upload_urls,
    get_upload_info,
    initiate_multipart_upload,
    patch_multipart_upload,
    start_multipart_upload,
)
from .utils import check_url  # noqa: F401
from .work_package import WorkPackageAccessor  # noqa: F401
