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

"""Utils to configure the FastAPI app"""

from email.utils import parseaddr

from fastapi import FastAPI

from ghga_service_commons.api import configure_app
from mass import metadata
from mass.adapters.inbound.fastapi_.routes import router
from mass.config import Config


def get_configured_app(*, config: Config) -> FastAPI:
    """Create and configure a REST API application."""
    title, summary = metadata["Summary"].split(" - ", 1)
    # authors given with name and email fill only Author-email, as "name <email>"
    name, email = parseaddr(metadata["Author-email"])
    author = metadata.get("Author") or name
    # a PEP 639 `license` string in pyproject.toml fills License-Expression, not License
    license = metadata.get("License-Expression") or metadata.get("License")
    contact = {"name": author, "email": email}
    license_info = {"name": license} if license else None
    version = metadata["Version"]

    app = FastAPI(
        contact=contact,
        license_info=license_info,
        summary=summary,
        title=title,
        version=version,
    )
    app.include_router(router)
    configure_app(app, config=config)

    return app
