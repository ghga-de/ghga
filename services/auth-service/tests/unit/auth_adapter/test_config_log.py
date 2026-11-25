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

"""Unit test that the startup log masks the secret config values"""

from logging import getLogger

import pytest
from jwcrypto import jwk

from auth_service.config import Config
from hexkit.log import configure_logging


def test_startup_log_masks_secrets(capsys: pytest.CaptureFixture[str]):
    """Test that the logged config shows neither the private key nor the password."""
    key = jwk.JWK.generate(kty="EC", crv="P-256")
    private_key = key.export(private_key=True, as_dict=True)["d"]
    config = Config(
        provide_apis=["ext_auth"],
        auth_key=key.export(private_key=True),
        basic_auth_credentials="alice:s3cret",
        log_format=None,
    )
    logger = getLogger("test_startup_log_masks_secrets")
    logger.propagate = False
    configure_logging(config=config, logger=logger)
    try:
        log = capsys.readouterr().err
    finally:
        logger.handlers.clear()
    assert "complete configuration" in log
    assert '"auth_key": "**********"' in log
    assert private_key not in log
    assert "s3cret" not in log
