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

"""Unit tests for the CLI"""

import pytest

from ucs import cli as cli_module


@pytest.fixture()
def cleanup_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, bool]]:
    """Replace `perform_cleanup` with a stand-in that records its arguments."""
    calls: list[dict[str, bool]] = []

    async def record_cleanup(**kwargs: bool) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(cli_module, "perform_cleanup", record_cleanup)
    return calls
