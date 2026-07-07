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

"""Test the stream_calc app via the CLI."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hexkit.providers.akafka.testutils import (
    KafkaFixture,
    kafka_container_fixture,  # noqa: F401
    kafka_fixture,  # noqa: F401
)
from sc_tests.integration.test_event_api import (
    CASES,
    check_problem_outcomes,
    submit_test_problems,
)

APP_DIR = Path(__file__).parent.parent.parent.absolute()


@pytest.mark.asyncio()
async def test_cli(kafka: KafkaFixture, monkeypatch: pytest.MonkeyPatch):
    """Test the stream_calc app via the CLI."""
    os.chdir(APP_DIR)
    kafka_server = kafka.kafka_servers[0]
    monkeypatch.setenv(name="STREAM_CALC_KAFKA_SERVERS", value=f'["{kafka_server}"]')
    # Only the app dir is needed; the subprocess runs the workspace venv interpreter,
    # which already resolves hexkit (and other deps) via its editable `.pth` files.
    # Appending site-packages here would defeat that `.pth` resolution under uv.
    monkeypatch.setenv(name="PYTHONPATH", value=str(APP_DIR))

    await submit_test_problems(CASES, kafka_server=kafka_server)

    # argv[0] must be the interpreter path (not "-m"): CPython locates its venv from
    # argv[0], and only then processes the editable `.pth` files that make hexkit
    # importable under uv. Passing executable= with argv[0]="-m" breaks that.
    with subprocess.Popen(
        args=[sys.executable, "-m", "stream_calc"],
    ) as process:
        await asyncio.wait_for(
            check_problem_outcomes(cases=CASES, kafka_server=kafka_server),
            10,
        )
        process.terminate()
