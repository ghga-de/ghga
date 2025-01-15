# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""General testing utilities"""

from pathlib import Path

from fastapi.testclient import TestClient

from ekss.adapters.inbound.fastapi_.deps import config_injector
from ekss.adapters.inbound.fastapi_.main import setup_app
from ekss.config import Config

BASE_DIR = Path(__file__).parent.resolve()


def get_test_client(config: Config) -> TestClient:
    """Return a configured TestClient instance"""
    app = setup_app(config)
    app.dependency_overrides[config_injector] = lambda: config
    return TestClient(app=app)
