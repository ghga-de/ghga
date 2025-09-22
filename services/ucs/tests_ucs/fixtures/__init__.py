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

"""Fixture definitions to aid in testing"""

from jwcrypto.jwk import JWK

from ucs.config import Config

__all__ = ["ConfigFixture"]


class ConfigFixture:
    config: Config
    wps_jwk: JWK
    uos_jwk: JWK

    def __init__(self, *, config: Config, wps_jwk: JWK, uos_jwk: JWK):
        self.config = config
        self.wps_jwk = wps_jwk
        self.uos_jwk = uos_jwk

    def update(self, **kwargs) -> Config:
        """Override specified values"""
        new_config = self.config.model_copy(update=kwargs)
        self.config = new_config
        return self.config
