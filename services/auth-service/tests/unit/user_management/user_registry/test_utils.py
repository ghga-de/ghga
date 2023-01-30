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

"""Unit tests for the utils module."""

from auth_service.user_management.user_registry.utils import (
    is_external_id,
    is_internal_id,
)


def test_is_internal_id():
    """Test that internal IDs can be validated."""
    assert is_internal_id(None) is False  # type: ignore
    assert is_internal_id(42) is False  # type: ignore
    assert is_internal_id("") is False
    assert is_internal_id("foo-bar") is False
    assert is_internal_id("foo-bar-baz-qux") is False
    assert is_internal_id("foo@bar.baz") is False
    assert is_internal_id("16fd2706-8baf-433b-82eb-8c7fada847da") is True
    assert is_internal_id("16fd2706-8baf-433b-82eb-8c7f@da847da") is False


def test_is_external_id():
    """Test that internal IDs can be validated."""
    assert is_external_id(None) is False  # type: ignore
    assert is_external_id(42) is False  # type: ignore
    assert is_external_id("") is False
    assert is_external_id("@") is False
    assert is_external_id("foo@bar.baz") is True
    assert is_external_id("foo@bar@baz") is False
    assert is_external_id("16fd2706-8baf-433b-82eb-8c7fada847da") is False
