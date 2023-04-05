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

"""Config utilies."""

from ghga_connector import core
from ghga_connector.config import Config

DEFAULT_TEST_CONFIG = Config(
    upload_api="http:/example.org/upload",
    download_api="http:/example.org/download",
    max_retries=0,
    max_wait_time=2,
    part_size=core.DEFAULT_PART_SIZE,
    server_pubkey="qx5g31H7rdsq7sgkew9ElkLIXvBje4RxDVcAHcJD8XY=",
    wps_file_list=["file1", "file2"],
    wps_file_endings=[".zip", ".tar.gz"],
    wps_user_id="user_1",
    wps_user_pubkey="P1oBHfr9AA37Kg8WW79RKKpDZlp77KoFx+n+3sLzPBY=",
)


def get_test_config(**kwargs):
    """Get test config params with the defaults being overwritting by the parameter
    passed as kwargs.
    """

    return DEFAULT_TEST_CONFIG.copy(update=kwargs)
