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

import warnings
from logging import getLogger

from pydantic import (
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveInt,
    model_validator,
)
from pydantic_settings import BaseSettings

log = getLogger(__name__)

RETIRED_COUNTER_FIELD = "retry_after_applicable_for_num_requests"
RETIRED_COUNTER_MESSAGE = (
    f"{RETIRED_COUNTER_FIELD} is ignored since 8.2.0 and will be removed in 9.0."
    " A Retry-After is now held as a deadline until it expires, rather than counted"
    " down over a number of requests. Remove it from your config."
)


class RateLimitingTransportConfig(BaseSettings):
    """Configuration for a rate limiting HTTPTransport.

    `min_request_interval` and `per_request_jitter` set how far apart a client spaces its
    requests. With the interval at 0, the jitter alone spreads them.
    """

    min_request_interval: NonNegativeFloat = Field(
        default=0.0,
        description="Minimum number of seconds between requests from one client."
        + " Leave at 0 to let per_request_jitter alone spread concurrent requests.",
    )
    per_request_jitter: NonNegativeFloat = Field(
        default=0.05,
        description="Upper bound of the random delay (in seconds) added to each request."
        + " With min_request_interval at 0 this is the only thing separating concurrent"
        + " requests. Set it to 0 to switch pacing off, e.g. when mocking in tests.",
    )
    retry_after_applicable_for_num_requests: PositiveInt = Field(
        default=1,
        deprecated=RETIRED_COUNTER_MESSAGE,
        description="Deprecated and ignored. A Retry-After is now held as a deadline"
        + " until it expires, rather than counted down over a number of requests.",
    )

    @model_validator(mode="after")
    def _warn_on_retired_counter(self) -> "RateLimitingTransportConfig":
        """Warn once at load time if the retired counter is still set.

        Pydantic's `deprecated` marker only fires on attribute access, and nothing reads
        this field any more.
        """
        if RETIRED_COUNTER_FIELD in self.model_fields_set:
            warnings.warn(RETIRED_COUNTER_MESSAGE, DeprecationWarning, stacklevel=2)
            log.warning(RETIRED_COUNTER_MESSAGE)
        return self


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
