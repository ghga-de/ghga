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

"""Contains common configuration for different composite async httpx Transports."""

from pydantic import Field, NonNegativeFloat, NonNegativeInt, PositiveInt
from pydantic_settings import BaseSettings


class CacheTransportConfig(BaseSettings):
    """Configuration options for the storage used in the caching transport.

    Currently only in memory storage is available.
    """

    client_cache_capacity: PositiveInt = Field(
        default=128,
        description="Maximum number of entries to store in the cache. Older entries are evicted once this limit is reached.",
    )
    client_cache_ttl: NonNegativeInt = Field(
        default=60,
        description="Number of seconds after which a stored response is considered stale.",
    )
    client_cacheable_methods: list[str] = Field(
        default=["POST", "GET"],
        description="HTTP methods for which responses are allowed to be cached.",
    )
    client_cacheable_status_codes: list[int] = Field(
        default=[200, 201],
        description="HTTP response status code for which responses are allowed to be cached.",
    )


class RateLimitingTransportConfig(BaseSettings):
    """Configuration options for a rate limiting HTTPTransport."""

    per_request_jitter: NonNegativeFloat = Field(
        default=0.0,
        description="Max amount of jitter (in seconds) to add to each request.",
    )
    retry_after_applicable_for_num_requests: PositiveInt = Field(
        default=1,
        description="Amount of requests after which the stored delay from a 429 response is ignored again. "
        + "Can be useful to adjust if concurrent requests are fired in quick succession.",
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


class CompositeCacheConfig(CompositeConfig, CacheTransportConfig):
    """Configuration for a transport providing retry, rate limiting and caching logic."""
