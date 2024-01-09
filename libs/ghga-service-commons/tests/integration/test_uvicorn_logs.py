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
"""Isolated test for uvicorn that spins up the server and verifies the log output."""
import asyncio
import json
from contextlib import suppress

import pytest
from fastapi import FastAPI
from hexkit.log import LoggingConfig, configure_logging

from ghga_service_commons.api.api import ApiConfigBase, configure_app, run_server

EXPECTED_FIELDS = {
    "timestamp",
    "service",
    "instance",
    "level",
    "correlation_id",
    "name",
    "message",
    "details",
}


@pytest.mark.asyncio
async def test_uvicorn_log_format(capsys):
    """Verify that the uvicorn logs are formatted with the configured logging."""
    test_app = FastAPI()
    config = ApiConfigBase()  # type: ignore

    configure_app(test_app, config)

    log_config = LoggingConfig(service_name="", service_instance_id="")
    configure_logging(config=log_config)
    capsys.readouterr()  # clear any captured output from stderr (e.g. logging config log)

    # Run the server just long enough to start up and generate initial uvicorn logs
    loop = asyncio.get_event_loop()
    task = loop.create_task(run_server(app=test_app, config=config))
    with suppress(asyncio.TimeoutError):
        await asyncio.wait_for(task, timeout=2)

    # Retrieve log output and strip any extra white space
    err = capsys.readouterr()[1].strip()

    # Get list of the different log messages
    assert err
    msgs = err.split("\n")

    for msg in msgs:
        # all logs should be json strings, something is wrong if not
        json_msg = json.loads(msg)
        if json_msg["name"].startswith("uvicorn"):
            # verify all expected fields exist and that all existing fields are expected
            assert set(json_msg) == EXPECTED_FIELDS
