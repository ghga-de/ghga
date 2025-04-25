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
#

"""Test deletion of claims."""

import logging

import pytest

from auth_service.claims_repository.core.deletion import (
    DatasetDeletionHandler,
)

from ...fixtures.utils import DummyClaimDao


@pytest.mark.asyncio()
async def test_deletion_handler(caplog: pytest.LogCaptureFixture):
    """Test the dataset deletion handler"""
    caplog.set_level(logging.INFO)
    records = caplog.records
    claim_dao = DummyClaimDao()
    handler = DatasetDeletionHandler(claim_dao=claim_dao)  # type: ignore
    await handler.handle_dataset_deletion(dataset_id="DS0819")
    assert len(records) == 1
    assert records[0].message == "Deleted 0 claims for dataset DS0819"
    caplog.clear()
    await handler.handle_dataset_deletion(dataset_id="DS0815")
    assert len(records) == 1
    assert records[0].message == "Deleted 1 claims for dataset DS0815"
    caplog.clear()
    await handler.handle_dataset_deletion(dataset_id="DS0815")
    assert len(records) == 1
    assert records[0].message == "Deleted 0 claims for dataset DS0815"
