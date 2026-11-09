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

"""Test the Vault test utils."""

import re

import pytest

from hexkit.providers.vault import testutils


# TODO: Remove `get_vault_fixture` when moving hexkit to v11.0.0
def test_get_vault_fixture_is_deprecated_alias_for_persistent(monkeypatch):
    """Test that get_vault_fixture warns and creates the persistent fixture."""
    calls = []

    def get_persistent_vault_fixture(**kwargs):
        calls.append(kwargs)
        return "persistent fixture"

    monkeypatch.setattr(
        testutils, "get_persistent_vault_fixture", get_persistent_vault_fixture
    )

    with pytest.deprecated_call(
        match=re.escape(testutils.GET_VAULT_FIXTURE_DEPRECATION_MESSAGE)
    ):
        fixture = testutils.get_vault_fixture(scope="module", name="my_vault")

    assert fixture == "persistent fixture"
    assert calls == [{"scope": "module", "name": "my_vault"}]
