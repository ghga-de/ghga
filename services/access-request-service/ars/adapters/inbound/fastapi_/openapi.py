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

"""Utils to customize the OpenAPI script"""

from typing import Any, Dict

from fastapi.openapi.utils import get_openapi

from ars import __version__
from ars.config import Config

__all__ = ["get_openapi_schema"]


def get_openapi_schema(api) -> Dict[str, Any]:
    """Generate a custom OpenAPI schema for the service."""

    config = Config()

    return get_openapi(
        title="Access Request Service",
        version=__version__,
        description="A service managing access requests for the GHGA Data Portal",
        servers=[{"url": config.api_root_path}],
        tags=[{"name": "AccessRequests"}],
        routes=api.routes,
    )
