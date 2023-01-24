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

"""Test file operations"""

from typing import Optional

import pytest
from ghga_service_chassis_lib.utils import big_temp_file

from ghga_connector.core.file_operations import read_file_parts


@pytest.mark.parametrize("from_part", (None, 3))
def test_read_file_parts(from_part: Optional[int]):
    """Test reading a full file with the `read_file_parts` function."""
    file_size = 20 * 1024 * 1024
    part_size = 5 * 1024 * 1024

    with big_temp_file(file_size) as file:

        # Get the expected content:
        initial_offset = 0 if from_part is None else part_size * (from_part - 1)
        file.seek(initial_offset)
        expected_content = file.read()
        file.seek(0)

        # read the file in parts:
        obtained_content = bytes()
        file_parts = (
            read_file_parts(file, part_size=part_size)
            if from_part is None
            else read_file_parts(file, part_size=part_size, from_part=from_part)
        )

        for part in file_parts:
            obtained_content += part

        assert expected_content == obtained_content
