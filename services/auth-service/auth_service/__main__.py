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

"""Entrypoint of the package"""

import asyncio
import datetime

from ghga_service_chassis_lib.api import run_server

from .config import CONFIG, Config


def assert_tz_is_utc():
    """Check that the default timezone is set to UTC."""
    if datetime.datetime.now().astimezone().tzinfo != datetime.timezone.utc:
        raise RuntimeError("System must be configured to use UTC.")


def run(config: Config = CONFIG):
    """Run the service"""
    assert_tz_is_utc()
    service = "auth_adapter" if config.run_auth_adapter else "user_management"
    print(f"Starting {service} service", service)
    print("Configuration:", CONFIG)
    asyncio.run(run_server(app=f"auth_service.{service}.api.main:app", config=config))


if __name__ == "__main__":
    run()
