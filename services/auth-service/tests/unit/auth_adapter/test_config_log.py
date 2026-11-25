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

from jwcrypto import jwk

from auth_service.config import Config


def test_config_dump_masks_secrets():
    """Test that the dump the startup log shows masks the key and the credentials."""
    key = jwk.JWK.generate(kty="EC", crv="P-256").export(private_key=True)
    config = Config(
        provide_apis=["ext_auth"],
        auth_key=key,
        basic_auth_credentials="alice:s3cret",
    )
    dump = config.model_dump(mode="json")
    assert dump["auth_key"] == "**********"
    assert dump["basic_auth_credentials"] == "**********"
