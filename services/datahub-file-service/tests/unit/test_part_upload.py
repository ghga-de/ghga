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
"""Unit tests for how the S3Client sends a re-encrypted part"""

import hashlib
import os
from unittest.mock import AsyncMock, MagicMock

import httpx2
import pytest

from dhfs.adapters.outbound.http import get_configured_httpx_client
from dhfs.adapters.outbound.s3 import PartBody, S3Client
from dhfs.constants import UPLOAD_CHUNK_SIZE
from tests.fixtures.config import get_config

pytestmark = pytest.mark.asyncio()

PART_URL = "https://s3.invalid/hub1-interrogation/object?partNumber=1"


async def test_part_body_is_chunked_and_can_be_sent_again():
    """Every iteration yields the whole part again, in chunks of at most 1 MiB."""
    data = os.urandom(2 * UPLOAD_CHUNK_SIZE + 1)
    body = PartBody(data)

    first = [chunk async for chunk in body]
    second = [chunk async for chunk in body]

    assert [len(chunk) for chunk in first] == [UPLOAD_CHUNK_SIZE, UPLOAD_CHUNK_SIZE, 1]
    assert b"".join(first) == data
    assert second == first


async def test_retried_part_upload_sends_the_whole_part_again():
    """A part upload the retry transport repeats must carry the whole part each time,
    with its length declared, and its URL must be presigned without the upload check.
    """
    part = bytearray(os.urandom(2 * UPLOAD_CHUNK_SIZE + 123))
    requests: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(503 if len(requests) == 1 else 200)

    config = get_config(client_exponential_backoff_max=0)
    storage = MagicMock()
    storage.get_part_upload_url = AsyncMock(return_value=PART_URL)
    async with get_configured_httpx_client(
        config=config, make_base_transport=lambda _: httpx2.MockTransport(handle)
    ) as client:
        s3_client = S3Client(config=config, object_storage=storage, httpx_client=client)
        await s3_client.upload_file_part(
            upload_id="upload",
            object_id="object",
            part_no=1,
            part_md5=hashlib.md5(part).digest(),
            part=part,
        )

    assert len(requests) == 2
    for request in requests:
        assert request.content == part
        assert request.headers["Content-Length"] == str(len(part))
        assert "Transfer-Encoding" not in request.headers
    storage.get_part_upload_url.assert_awaited_once()
    assert storage.get_part_upload_url.await_args.kwargs["verify_upload"] is False
