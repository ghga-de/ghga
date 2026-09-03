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

"""Contains common configuration for different composite async httpx2 Transports."""

from logging import getLogger

from pydantic import (
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveInt,
)
from pydantic_settings import BaseSettings

log = getLogger(__name__)

RETIRED_FIELD = "retry_after_applicable_for_num_requests"
RETIRED_FIELD_MESSAGE = (
    f"{RETIRED_FIELD} is ignored since 8.2.0 and will be removed in 9.0."
)


class RateLimitingTransportConfig(BaseSettings):
    """Configuration for a rate limiting HTTPTransport."""

    min_request_interval: NonNegativeFloat = Field(
        default=0.0,
        description="Minimum number of seconds between requests from one client."
        + "If left at 0 some jitter is still added to pace concurrent requests.",
    )
    per_request_jitter: NonNegativeFloat = Field(
        default=0.05,
        description="Max amount of jitter (in seconds) to add to each request.",
    )
    retry_after_applicable_for_num_requests: PositiveInt = Field(
        default=1,
        deprecated=RETIRED_FIELD_MESSAGE,
        description="Deprecated and no longer applicable. Remove from your config, "
        + "will be removed in service-commons 9.0.0.",
    )


class RetryTransportConfig(BaseSettings):
    """Configuration options for an HTTPTransport providing retry logic."""

    client_exponential_backoff_max: NonNegativeInt = Field(
        default=60,
        description="Maximum number of seconds to wait between retries when using"
        + " exponential backoff retry strategies. The client timeout might need to be adjusted accordingly.",
    )
    client_num_retries: NonNegativeInt = Field(
        default=3, description="Number of times to retry failed API calls."
    )
    client_retry_status_codes: list[NonNegativeInt] = Field(
        default=[408, 429, 500, 502, 503, 504],
        description="List of status codes that should trigger retrying a request.",
    )
    client_reraise_from_retry_error: bool = Field(
        default=True,
        description="Specifies if the exception wrapped in the final RetryError is reraised "
        "or the RetryError is returned as is.",
    )


class CompositeConfig(RateLimitingTransportConfig, RetryTransportConfig):
    """Configuration for a transport providing both retry and rate limiting logic."""
