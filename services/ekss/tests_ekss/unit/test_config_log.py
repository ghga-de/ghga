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

"""Unit test that the startup log masks the secret config values"""

from logging import getLogger

import pytest

from ekss.config import Crypt4GHConfig
from hexkit.log import configure_logging
from tests_ekss.fixtures.config import DEFAULT_CONFIG, get_config

PASSPHRASE = "correct-horse-battery-staple"


def test_startup_log_masks_passphrase(capsys: pytest.CaptureFixture[str]):
    """Test that the logged config does not show the key file passphrase."""
    config = get_config(
        [
            Crypt4GHConfig(
                server_private_key_path=DEFAULT_CONFIG.server_private_key_path,
                private_key_passphrase=PASSPHRASE,
            )
        ]
    )
    config = config.model_copy(update={"log_format": None})
    logger = getLogger("test_startup_log_masks_passphrase")
    logger.propagate = False
    configure_logging(config=config, logger=logger)
    try:
        log = capsys.readouterr().err
    finally:
        logger.handlers.clear()
    assert '"private_key_passphrase": "**********"' in log
    assert PASSPHRASE not in log
