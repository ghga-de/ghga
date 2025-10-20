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

"""Global Config Parameters"""

from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any

import httpx
from hexkit.config import config_from_yaml
from hexkit.utils import set_context_var
from pydantic import Field, NonNegativeInt, PositiveInt
from pydantic_settings import BaseSettings

from ghga_connector import exceptions
from ghga_connector.constants import DEFAULT_PART_SIZE, MAX_RETRIES, MAX_WAIT_TIME

__all__ = [
    "CONFIG",
    "Config",
    "get_download_api_url",
    "get_ghga_pubkey",
    "get_upload_api_url",
    "get_work_package_api_url",
    "set_runtime_config",
]

upload_api_url_var: ContextVar[str] = ContextVar("upload_api_url_var", default="")
download_api_url_var: ContextVar[str] = ContextVar("download_api_url_var", default="")
work_package_api_url_var: ContextVar[str] = ContextVar(
    "work_package_api_url_var", default=""
)
ghga_pubkey_var: ContextVar[str] = ContextVar("ghga_pubkey", default="")


def _get_context_var(context_var: ContextVar) -> Any:
    value = context_var.get()
    if not value:
        raise ValueError(f"{context_var.name} is not set")
    return value


def get_upload_api_url() -> str:
    """Get the Upload API URL."""
    return _get_context_var(upload_api_url_var)


def get_download_api_url() -> str:
    """Get the Download API URL."""
    return _get_context_var(download_api_url_var)


def get_work_package_api_url() -> str:
    """Get the Work Package API URL."""
    return _get_context_var(work_package_api_url_var)


def get_ghga_pubkey() -> str:
    """Get the GHGA crypt4gh public key."""
    return _get_context_var(ghga_pubkey_var)


@config_from_yaml(prefix="ghga_connector")
class Config(BaseSettings):
    """Global Config Parameters"""

    max_concurrent_downloads: PositiveInt = Field(
        default=5, description="Number of parallel downloader tasks for file parts."
    )
    max_retries: NonNegativeInt = Field(
        default=MAX_RETRIES, description="Number of times to retry failed API calls."
    )
    max_wait_time: PositiveInt = Field(
        default=MAX_WAIT_TIME,
        description="Maximum time in seconds to wait before quitting without a download.",
    )
    part_size: PositiveInt = Field(
        default=DEFAULT_PART_SIZE, description="The part size to use for download."
    )
    wkvs_api_url: str = Field(
        default="https://data.ghga.de/.well-known",
        description="URL to the root of the WKVS API. Should start with https://",
    )
    exponential_backoff_max: NonNegativeInt = Field(
        default=60,
        description="Maximum number of seconds to wait for when using exponential backoff retry strategies.",
    )
    retry_status_codes: list[NonNegativeInt] = Field(
        default=[408, 500, 502, 503, 504],
        description="List of status codes that should trigger retrying a request.",
    )


CONFIG = Config()


@asynccontextmanager
async def set_runtime_config(client: httpx.AsyncClient):
    """Set runtime config as context vars to be accessed within a context manager.

    This sets the following values:
    - ghga_pubkey
    - work_package_api_url
    - download_api_url
    - upload_api_url

    Raises:
        WellKnownValueNotFound: If one of the well-known values is not found in the
            response from the WKVS.
        BadResponseCodeError: If the status code returned is not 200
        ConnectionFailedError: If the request fails due to a timeout/connection problem
        RequestFailedError: If the request fails for any other reason
    """
    values = await _get_wkvs_values(client)
    for value_name in [
        "crypt4gh_public_key",
        "wps_api_url",
        "dcs_api_url",
        "ucs_api_url",
    ]:
        if value_name not in values:
            raise exceptions.WellKnownValueNotFound(value_name=value_name)

    async with (
        set_context_var(ghga_pubkey_var, values["crypt4gh_public_key"]),
        set_context_var(work_package_api_url_var, values["wps_api_url"].rstrip("/")),
        set_context_var(download_api_url_var, values["dcs_api_url"].rstrip("/")),
        set_context_var(upload_api_url_var, values["ucs_api_url"].rstrip("/")),
    ):
        yield


async def _get_wkvs_values(client: httpx.AsyncClient) -> dict[str, Any]:
    """Retrieve a value from the well-known-value-service using the supplied client.

    Raises:
        BadResponseCodeError: If the status code returned is not 200
        ConnectionFailedError: If the request fails due to a timeout/connection problem
        RequestFailedError: If the request fails for any other reason
    """
    url = f"{CONFIG.wkvs_api_url}/values"

    try:
        response = await client.get(url)
    except httpx.RequestError as request_error:
        exceptions.raise_if_connection_failed(request_error=request_error, url=url)
        raise exceptions.RequestFailedError(url=url) from request_error

    if response.status_code != 200:
        raise exceptions.BadResponseCodeError(
            url=url, response_code=response.status_code
        )

    return response.json()
