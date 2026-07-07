# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Constants used throughout the core."""

from math import ceil

import crypt4gh.lib

DEFAULT_PART_SIZE = 64 * (1024**2)  # 64 MiB
TIMEOUT = 60.0
TIMEOUT_LONG = 5 * TIMEOUT + 10
MAX_PART_NUMBER = 10000
MAX_RETRIES = 5  # retries for a single file part at the HTTP layer (see uploader.py)
MAX_WAIT_TIME = 60 * 60
MAX_UPLOAD_BACKOFF_SEC = 360
UPLOAD_RETRY_BACKOFF_SEC = 5
# Batch upload: how many times a failed file is retried, and how long to wait between
#  retry passes. Kept separate from the part-level retry constants above so the two can
#  be tuned independently.
DEFAULT_BATCH_MAX_RETRIES = 3
BATCH_RETRY_BACKOFF_SEC = 5
C4GH = ".c4gh"
CACHE_MIN_FRESH = 3
DOWNLOAD_URL_LIFESPAN = 60  # 1 minute
DOWNLOAD_URL_CACHE_TIME = DOWNLOAD_URL_LIFESPAN - CACHE_MIN_FRESH
DOWNLOAD_URL_CACHE_SIZE = 250
UPLOAD_WOT_LIFESPAN = 30  # The WPS default of 30 seconds
UPLOAD_WOT_CACHE_TIME = UPLOAD_WOT_LIFESPAN - CACHE_MIN_FRESH
UPLOAD_WOT_CACHE_SIZE = 250
# Page size used when listing a FileUploadBox's uploads. The Upload API paginates this
#  endpoint and caps the limit at 100, so request the maximum to minimize round trips.
UPLOAD_LISTING_PAGE_SIZE = 100
ENVELOPE_SIZE = 124  # for one recipient (i.e. GHGA)
MIN_PART_SIZE = 5 * 1024**2  # 5 MiB (S3 minimum for multipart parts)
MAX_PART_SIZE = 5 * 1024**3  # 5 GiB (S3 maximum for multipart parts)
MIN_ALIGNED_PART_SIZE = (  # smallest cipher-segment-aligned part size
    ceil(MIN_PART_SIZE / crypt4gh.lib.CIPHER_SEGMENT_SIZE)
    * crypt4gh.lib.CIPHER_SEGMENT_SIZE
)
MAX_ALIGNED_PART_SIZE = (  # largest cipher-segment-aligned part size
    MAX_PART_SIZE // crypt4gh.lib.CIPHER_SEGMENT_SIZE
) * crypt4gh.lib.CIPHER_SEGMENT_SIZE
