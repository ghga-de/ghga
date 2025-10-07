# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test file operations"""

from asyncio import create_task
from unittest.mock import AsyncMock, Mock

import pytest

from ghga_connector.core import (
    PartRange,
    WorkPackageAccessor,
    async_client,
    calc_part_ranges,
)
from ghga_connector.core.downloading.downloader import Downloader, TaskHandler
from ghga_connector.core.downloading.structs import URLResponse
from ghga_connector.core.progress_bar import DownloadProgressBar
from ghga_connector.exceptions import DownloadError
from tests.fixtures.s3 import (  # noqa: F401
    S3Fixture,
    get_big_s3_object,
    reset_state,
    s3_fixture,
)


@pytest.mark.parametrize(
    "start, end, file_size",
    [
        # download full file as one part
        (0, 20 * 1024 * 1024 - 1, 20 * 1024 * 1024),
        (  # download intermediate part:
            5 * 1024 * 1024,
            10 * 1024 * 1024 - 1,
            20 * 1024 * 1024,
        ),
    ],
)
@pytest.mark.asyncio
async def test_download_content_range(
    start: int,
    end: int,
    file_size: int,
    s3_fixture: S3Fixture,  # noqa: F811
):
    """Test the `download_content_range` function."""
    # prepare state and the expected result:
    big_object = await get_big_s3_object(s3_fixture, object_size=file_size)
    expected_bytes = big_object.content[start : end + 1]
    download_url = await s3_fixture.storage.get_object_download_url(
        object_id=big_object.object_id, bucket_id=big_object.bucket_id
    )

    # download content range with dedicated function:
    async with async_client() as client:
        # no work package accessor calls in download_content_range, just mock for correct type
        dummy_accessor = Mock(spec=WorkPackageAccessor)
        downloader = Downloader(
            client=client,
            file_id=big_object.object_id,
            max_concurrent_downloads=5,
            work_package_accessor=dummy_accessor,
        )
        await downloader.download_content_range(url=download_url, start=start, end=end)

    result = await downloader._queue.get()
    assert not isinstance(result, BaseException)

    obtained_start, obtained_bytes = result

    assert start == obtained_start
    assert expected_bytes == obtained_bytes


@pytest.mark.parametrize(
    "part_size",
    [1 * 1024 * 1024, 3 * 1024 * 1024, 5 * 1024 * 1024],
)
@pytest.mark.asyncio(loop_scope="session")
async def test_download_file_parts(
    part_size: int,
    s3_fixture: S3Fixture,  # noqa: F811
    tmp_path,
):
    """Test the `download_file_parts` function."""
    # prepare state and the expected result:
    big_object = await get_big_s3_object(s3_fixture)
    total_file_size = len(big_object.content)
    expected_bytes = big_object.content
    part_ranges = calc_part_ranges(part_size=part_size, total_file_size=total_file_size)
    download_url = await s3_fixture.storage.get_object_download_url(
        object_id=big_object.object_id, bucket_id=big_object.bucket_id
    )
    url_response = URLResponse(download_url, total_file_size)
    mock_fetch = AsyncMock(return_value=url_response)

    async with async_client() as client:
        # no work package accessor calls in download_file_parts, just mock for correct type
        dummy_accessor = Mock(spec=WorkPackageAccessor)
        downloader = Downloader(
            client=client,
            file_id=big_object.object_id,
            max_concurrent_downloads=5,
            work_package_accessor=dummy_accessor,
        )
        downloader.fetch_download_url = mock_fetch  # type: ignore
        task_handler = TaskHandler()

        for part_range in part_ranges:
            task_handler.schedule(downloader.download_to_queue(part_range=part_range))

        file_path = tmp_path / "test.file"
        with (
            file_path.open("wb") as file,
            DownloadProgressBar(
                file_name=file.name, file_size=total_file_size
            ) as progress_bar,
        ):
            dl_task = create_task(
                downloader.drain_queue_to_file(
                    file=file,
                    file_size=total_file_size,
                    offset=0,
                    progress_bar=progress_bar,
                )
            )
            await task_handler.gather()
            await dl_task

        num_bytes_obtained = file_path.stat().st_size
        assert num_bytes_obtained == len(expected_bytes)

        # test exception in the beginning
        downloader = Downloader(
            client=client,
            file_id=big_object.object_id,
            max_concurrent_downloads=5,
            work_package_accessor=dummy_accessor,
        )
        downloader.fetch_download_url = mock_fetch  # type: ignore
        task_handler = TaskHandler()
        part_ranges = calc_part_ranges(
            part_size=part_size, total_file_size=total_file_size
        )

        task_handler.schedule(
            downloader.download_to_queue(part_range=PartRange(-10000, -1))
        )
        task_handler.schedule(
            downloader.download_to_queue(part_range=next(part_ranges))
        )

        file_path = tmp_path / "test2.file"
        with (
            file_path.open("wb") as file,
            DownloadProgressBar(
                file_name=file.name, file_size=total_file_size
            ) as progress_bar,
        ):
            dl_task = create_task(
                downloader.drain_queue_to_file(
                    file=file,
                    file_size=total_file_size,
                    offset=0,
                    progress_bar=progress_bar,
                )
            )
            with pytest.raises(DownloadError):
                try:
                    await task_handler.gather()
                except:
                    dl_task.cancel()
                    raise
                else:
                    await dl_task

        # test exception at the end
        downloader = Downloader(
            client=client,
            file_id=big_object.object_id,
            max_concurrent_downloads=5,
            work_package_accessor=dummy_accessor,
        )
        downloader.fetch_download_url = mock_fetch  # type: ignore
        task_handler = TaskHandler()
        part_ranges = calc_part_ranges(
            part_size=part_size, total_file_size=total_file_size
        )
        part_ranges = list(part_ranges)  # type: ignore
        for idx, part_range in enumerate(part_ranges):
            if idx == len(part_ranges) - 1:  # type: ignore
                task_handler.schedule(
                    downloader.download_to_queue(part_range=PartRange(-10000, -1))
                )
            else:
                task_handler.schedule(
                    downloader.download_to_queue(part_range=part_range)
                )

        file_path = tmp_path / "test3.file"
        with (
            file_path.open("wb") as file,
            DownloadProgressBar(
                file_name=file.name, file_size=total_file_size
            ) as progress_bar,
        ):
            dl_task = create_task(
                downloader.drain_queue_to_file(
                    file=file,
                    file_size=total_file_size,
                    offset=0,
                    progress_bar=progress_bar,
                )
            )
            with pytest.raises(DownloadError):
                try:
                    await task_handler.gather()
                except:
                    dl_task.cancel()
                    raise
                else:
                    await dl_task
