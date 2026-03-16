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

"""Unit tests for parse_file_info_for_upload() and upload_files() in main.py"""

from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import httpx
import pytest

from ghga_connector import exceptions
from ghga_connector.core.main import parse_file_info_for_upload, upload_files
from ghga_connector.core.uploading.structs import CoreFileInfo, FileInfoForUpload
from tests.fixtures import set_runtime_test_config  # noqa: F401
from tests.fixtures.config import get_test_config
from tests.fixtures.utils import PRIVATE_KEY_FILE, PUBLIC_KEY_FILE


def test_parse_file_info_path_only_uses_filename_as_alias():
    """Make sure the filename is used as the alias when no alias is given."""
    with NamedTemporaryFile(suffix=".fastq") as f:
        result = parse_file_info_for_upload([f.name])
    assert len(result) == 1
    assert result[0].alias == Path(f.name).name
    assert result[0].path == Path(f.name).resolve()


def test_parse_file_info_alias_comma_path_format():
    """Make sure the 'alias,path' format correctly sets a custom alias."""
    with NamedTemporaryFile() as f:
        result = parse_file_info_for_upload([f"my-alias,{f.name}"])
    assert result[0].alias == "my-alias"
    assert result[0].path == Path(f.name).resolve()


def test_parse_file_info_alias_with_empty_path_raises():
    """Make sure 'alias,' with only whitespace after the comma raises RuntimeError."""
    with pytest.raises(RuntimeError, match="No path supplied"):
        parse_file_info_for_upload(["my-alias, "])


def test_parse_file_info_nonexistent_file_raises():
    """Make sure a path pointing to a non-existent file raises FileDoesNotExistError."""
    with pytest.raises(exceptions.FileDoesNotExistError):
        parse_file_info_for_upload(["/tmp/definitely_does_not_exist_xyz_123.fastq"])


def test_parse_file_info_duplicate_alias_raises():
    """Make sure duplicate aliases in the input raise a ValueError."""
    with NamedTemporaryFile(suffix=".a") as f1, NamedTemporaryFile(suffix=".b") as f2:
        with pytest.raises(ValueError, match="Duplicate alias"):
            parse_file_info_for_upload(
                [f"same-alias,{f1.name}", f"same-alias,{f2.name}"]
            )


def test_parse_file_info_duplicate_path_raises():
    """Make sure the same file path appearing under two different aliases raises a ValueError."""
    with NamedTemporaryFile() as f:
        with pytest.raises(ValueError, match="Duplicate path"):
            parse_file_info_for_upload([f"alias-one,{f.name}", f"alias-two,{f.name}"])


def test_parse_file_info_skips_empty_strings():
    """Make sure empty strings in the input list are silently ignored."""
    with NamedTemporaryFile() as f:
        result = parse_file_info_for_upload(["", f.name, ""])
    assert len(result) == 1


def test_parse_file_info_decrypted_size_matches_file():
    """Make sure the decrypted_size recorded in the result matches the actual file size on disk."""
    with NamedTemporaryFile() as f:
        content = b"hello world"
        f.write(content)
        f.flush()
        result = parse_file_info_for_upload([f.name])
    assert result[0].decrypted_size == len(content)


@pytest.mark.asyncio
async def test_upload_files_applies_config_part_size(
    set_runtime_test_config,  # noqa: F811
):
    """Make sure upload_files wraps each CoreFileInfo with the configured part_size from Config."""
    test_part_size = 12 * 1024 * 1024  # 12 MiB — a value distinct from the default
    captured: list[FileInfoForUpload] = []

    async def mock_upload_files_from_list(
        *, upload_client, file_info_list, my_private_key, max_concurrent_uploads
    ):
        captured.extend(file_info_list)

    with (
        NamedTemporaryFile() as f,
        patch(
            "ghga_connector.core.main.upload_files_from_list",
            mock_upload_files_from_list,
        ),
        patch(
            "ghga_connector.core.uploading.api_calls.is_service_healthy",
            return_value=True,
        ),
        patch(
            "ghga_connector.config.CONFIG", get_test_config(part_size=test_part_size)
        ),
        patch("ghga_connector.core.main.WorkPackageClient"),
    ):
        f.write(b"data")
        f.flush()
        core_file_info = CoreFileInfo(alias="test", path=Path(f.name), decrypted_size=4)
        async with httpx.AsyncClient() as client:
            await upload_files(
                client=client,
                core_file_info_list=[core_file_info],
                my_public_key_path=PUBLIC_KEY_FILE,
                my_private_key_path=PRIVATE_KEY_FILE,
                passphrase=None,
            )

    assert len(captured) == 1
    assert captured[0].configured_part_size == test_part_size
