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

"""Unit tests for the REST API."""

from unittest.mock import AsyncMock

import pytest
from ghga_service_commons.api.testing import AsyncTestClient

from rts.inject import prepare_rest_app
from rts.ports.inbound.rev_tran import ReverseTranspilerPort
from tests.fixtures.config import get_config

pytestmark = pytest.mark.asyncio()


async def test_data_does_not_exist():
    """Test the case where data does not exist."""
    config = get_config()
    core = AsyncMock()
    accession = "test_accession"
    core.retrieve_workbook.side_effect = ReverseTranspilerPort.MetadataNotFoundError(
        study_accession=accession
    )
    async with (
        prepare_rest_app(config=config, reverse_transpiler_override=core) as app,
        AsyncTestClient(app) as client,
    ):
        response = await client.get(f"/studies/{accession}")
        assert response.status_code == 404
        assert response.json() == {
            "exception_id": "metadataNotFoundError",
            "description": "Metadata for study accession not found.",
            "data": {"study_accession": accession},
        }
