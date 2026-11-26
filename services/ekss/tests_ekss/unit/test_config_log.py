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

"""Unit test that the config masks its secret values in the startup log"""

from tests_ekss.fixtures.config import DEFAULT_CONFIG


def test_config_dump_masks_passphrase():
    """Test that the dump the startup log shows masks the key file passphrase."""
    assert DEFAULT_CONFIG.private_key_passphrase
    dump = DEFAULT_CONFIG.model_dump(mode="json")
    assert dump["private_key_passphrase"] == "**********"
