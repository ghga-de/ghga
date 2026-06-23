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

"""Unit tests for custom exceptions and exception helpers."""

import httpx

from ghga_connector import exceptions


def test_reason_from_exception_uses_message_when_present():
    """Ensure a non-empty exception message is used verbatim as the reason."""
    assert exceptions.extract_reason(RuntimeError("boom")) == "boom"


def test_reason_from_exception_falls_back_to_type_for_blank_message():
    """Ensure an exception with an empty message falls back to its qualified type name."""
    reason = exceptions.extract_reason(httpx.ReadError(""))

    assert reason  # assert not empty
    assert "httpx.ReadError" in reason
