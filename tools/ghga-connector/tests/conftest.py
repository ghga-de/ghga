# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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
"""Configuration for the global RequestsSession"""

import pytest

from ghga_connector.core import MAX_RETRIES, RequestsSession


@pytest.fixture(autouse=True)
def default_session_configuration():
    """Configure requests session with default number of max_retries"""
    RequestsSession.configure(max_retries=MAX_RETRIES)
