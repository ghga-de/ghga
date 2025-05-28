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

"""Test progress bar wrapper implementation."""

from math import ceil
from time import sleep

from ghga_connector.core.downloading.progress_bar import ProgressBar


def test_progress_bar():
    """Test progress bar with dummy data"""
    file_name = "test_file.gz"
    file_size = 1024**3
    chunk_size = 100 * 1024**2

    with ProgressBar(file_name=file_name, file_size=file_size) as progress:
        for _ in range(ceil(file_size / chunk_size)):
            progress.advance(chunk_size)
            sleep(0.1)

        assert progress._progress.finished
        assert progress._progress.tasks[0].completed == file_size
