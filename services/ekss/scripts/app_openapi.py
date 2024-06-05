#!/usr/bin/env python3

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

"""Used to define the location of the main FastAPI app object."""

import json
from typing import Any

from ekss.adapters.inbound.fastapi_.custom_openapi import get_openapi_schema
from ekss.adapters.inbound.fastapi_.main import setup_app
from ekss.config import CONFIG

app = setup_app(CONFIG)

__all__ = ["app"]


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi_schema(app)
    app.openapi_schema = openapi_schema
    return openapi_schema


def main():
    """Print the openapi"""
    print(json.dumps(custom_openapi()))


if __name__ == "__main__":
    main()
