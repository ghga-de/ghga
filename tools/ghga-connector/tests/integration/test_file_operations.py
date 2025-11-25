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
from typing import Any
from unittest.mock import Mock, patch

import pytest

from ghga_connector.config import set_runtime_config
from ghga_connector.core import (
    PartRange,
    WorkPackageClient,
    async_client,
    calc_part_ranges,
)
from ghga_connector.core.downloading.api_calls import DownloadClient
from ghga_connector.core.downloading.downloader import Downloader, TaskHandler
from ghga_connector.exceptions import DownloadError
from tests.fixtures.config import get_test_config
from tests.fixtures.mock_api.app import mock_external_calls  # noqa: F401
from tests.fixtures.s3 import (  # noqa: F401
    S3Fixture,
    get_big_s3_object,
    reset_state,
    s3_fixture,
)


@pytest.fixture(scope="function", autouse=True)
def apply_test_config():
    """Apply default test config"""
    with patch("ghga_connector.config.CONFIG", get_test_config()):
        yield


def fetch_download_url_mock(return_value: Any):
    """Patch for fetch_download_url instead of setting up an AsyncMock or using a lambda"""

    async def inner(*args, **kwargs):
        return return_value

    return inner


@pytest.mark.parametrize(
    "start, stop, file_size",
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
async def test_download_to_queue(
    start: int,
    stop: int,
    file_size: int,
    s3_fixture: S3Fixture,  # noqa: F811
    mock_external_calls,  # noqa: F811
    monkeypatch,
):
    """Test the `_download_to_queue` function."""
    # prepare state and the expected result:
    big_object = await get_big_s3_object(s3_fixture, object_size=file_size)
    expected_bytes = big_object.content[start : stop + 1]
    download_url = await s3_fixture.storage.get_object_download_url(
        object_id=big_object.object_id, bucket_id=big_object.bucket_id
    )

    # download content range with dedicated function:
    async with async_client() as client, set_runtime_config(client=client):
        # no work package work_pkg_client calls in download_content_range, just mock for correct type
        dummy_work_pkg_client = Mock(spec=WorkPackageClient)
        download_client = DownloadClient(
            client=client, work_package_client=dummy_work_pkg_client
        )
        downloader = Downloader(
            download_client=download_client,
            file_id=big_object.object_id,
            file_size=len(expected_bytes),
            max_concurrent_downloads=5,
        )
        monkeypatch.setattr(
            downloader, "fetch_download_url", fetch_download_url_mock(download_url)
        )
        await downloader._download_to_queue(
            part_range=PartRange(start=start, stop=stop)
        )

    result = await downloader._queue.get()
    assert not isinstance(result, BaseException)

    obtained_start, obtained_bytes = result

    assert obtained_start == start
    assert obtained_bytes == expected_bytes


@pytest.mark.parametrize(
    "part_size",
    [1 * 1024 * 1024, 3 * 1024 * 1024, 5 * 1024 * 1024],
)
@pytest.mark.asyncio(loop_scope="session")
async def test_download_file_parts(
    part_size: int,
    s3_fixture: S3Fixture,  # noqa: F811
    tmp_path,
    mock_external_calls,  # noqa: F811
    monkeypatch,
):
    """Test the `_download_to_queue` function with multiple file parts and an
    actual TaskHandler instance.
    """
    # TODO: [later] See about decomposing this test into smaller tests
    # prepare state and the expected result:
    big_object = await get_big_s3_object(s3_fixture)
    total_file_size = len(big_object.content)
    expected_bytes = big_object.content
    part_ranges = calc_part_ranges(part_size=part_size, total_file_size=total_file_size)
    download_url = await s3_fixture.storage.get_object_download_url(
        object_id=big_object.object_id, bucket_id=big_object.bucket_id
    )

    async with async_client() as client, set_runtime_config(client=client):
        # no work package work_pkg_client calls in download_file_parts, just mock for correct type
        dummy_work_pkg_client = Mock(spec=WorkPackageClient)
        download_client = DownloadClient(
            client=client, work_package_client=dummy_work_pkg_client
        )
        downloader = Downloader(
            download_client=download_client,
            file_id=big_object.object_id,
            file_size=len(expected_bytes),
            max_concurrent_downloads=5,
        )
        monkeypatch.setattr(
            downloader, "fetch_download_url", fetch_download_url_mock(download_url)
        )
        task_handler = TaskHandler()

        for part_range in part_ranges:
            task_handler.schedule(downloader._download_to_queue(part_range=part_range))

        file_path = tmp_path / "test.file"
        with file_path.open("wb") as file:
            dl_task = create_task(
                downloader._drain_queue_to_file(
                    file=file,
                    file_size=total_file_size,
                    offset=0,
                )
            )
            await task_handler.gather()
            await dl_task

        num_bytes_obtained = file_path.stat().st_size
        assert num_bytes_obtained == len(expected_bytes)

        # test exception in the beginning
        downloader = Downloader(
            download_client=download_client,
            file_id=big_object.object_id,
            file_size=len(expected_bytes),
            max_concurrent_downloads=5,
        )
        monkeypatch.setattr(
            downloader, "fetch_download_url", fetch_download_url_mock(download_url)
        )
        task_handler = TaskHandler()
        part_ranges = calc_part_ranges(
            part_size=part_size, total_file_size=total_file_size
        )

        task_handler.schedule(
            downloader._download_to_queue(part_range=PartRange(-10000, -1))
        )
        task_handler.schedule(
            downloader._download_to_queue(part_range=next(part_ranges))
        )

        file_path = tmp_path / "test2.file"
        with file_path.open("wb") as file:
            dl_task = create_task(
                downloader._drain_queue_to_file(
                    file=file,
                    file_size=total_file_size,
                    offset=0,
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
            download_client=download_client,
            file_id=big_object.object_id,
            file_size=len(expected_bytes),
            max_concurrent_downloads=5,
        )
        monkeypatch.setattr(
            downloader, "fetch_download_url", fetch_download_url_mock(download_url)
        )
        task_handler = TaskHandler()
        part_ranges = calc_part_ranges(
            part_size=part_size, total_file_size=total_file_size
        )
        part_ranges = list(part_ranges)  # type: ignore
        for idx, part_range in enumerate(part_ranges):
            if idx == len(part_ranges) - 1:  # type: ignore
                task_handler.schedule(
                    downloader._download_to_queue(part_range=PartRange(-10000, -1))
                )
            else:
                task_handler.schedule(
                    downloader._download_to_queue(part_range=part_range)
                )

        file_path = tmp_path / "test3.file"
        with file_path.open("wb") as file:
            dl_task = create_task(
                downloader._drain_queue_to_file(
                    file=file,
                    file_size=total_file_size,
                    offset=0,
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
