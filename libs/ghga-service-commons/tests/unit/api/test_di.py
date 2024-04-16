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
#

"""Testing the di utils from the api subpackage."""

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI

from ghga_service_commons.api.di import DependencyDummy
from ghga_service_commons.api.testing import AsyncTestClient

dummy_dependency = DependencyDummy("dummy")


def test_dependency_dummy_repr():
    """Test that the DependencyDummy has a useful repr."""
    assert repr(dummy_dependency) == "DependencyDummy('dummy')"


@pytest.mark.asyncio
async def test_dependency_dummy_no_override():
    """Test that using a DependencyDummy in a FastAPI app raises an error if it is not
    overridden.
    """
    app = FastAPI()

    @app.get("/")
    async def get_dummy(dummy: Annotated[str, Depends(dummy_dependency)]):
        """Dummy view function that uses a DependencyDummy."""
        return dummy

    client = AsyncTestClient(app)
    with pytest.raises(RuntimeError, match="'dummy' was not replaced"):
        await client.get("/")


@pytest.mark.asyncio
async def test_dependency_dummy_override():
    """Test that using a DependencyDummy in a FastAPI app does not raise an error if it
    is overridden.
    """
    value = "test"

    app = FastAPI()

    @app.get("/")
    async def get_dummy(dummy: Annotated[str, Depends(dummy_dependency)]):
        """Dummy view function that uses a DependencyDummy."""
        assert dummy is value
        return dummy

    app.dependency_overrides[dummy_dependency] = lambda: value
    client = AsyncTestClient(app)
    response = await client.get("/")

    assert response.status_code == 200
