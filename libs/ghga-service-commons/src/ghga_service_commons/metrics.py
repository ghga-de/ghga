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

"""OpenTelemetry metrics helpers. Requires the `metrics` extra.

The metrics only go somewhere once a MeterProvider is set, for instance by
`hexkit.opentelemetry.configure_opentelemetry` with `enable_otel_metrics` on.
Until then the OpenTelemetry API records into a no-op meter.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress

from opentelemetry.metrics import Meter, get_meter

__all__ = ["refresh_gauge"]

log = logging.getLogger(__name__)


@asynccontextmanager
async def refresh_gauge(  # noqa: PLR0913
    *,
    name: str,
    description: str,
    read: Callable[[], Awaitable[float]],
    unit: str = "",
    interval: float = 30,
    timeout: float = 10,
    meter: Meter | None = None,
) -> AsyncIterator[None]:
    """Keep a gauge set to the value of an async source while the context is open.

    `read` is awaited on entry and then every `interval` seconds in a background task
    on the running event loop, so the source can be any coroutine, such as a database
    count. An exporter only ever reads the last value set and never waits on `read`.

    A call that fails or takes longer than `timeout` seconds is logged as a warning
    and leaves the gauge at its previous value until the next call succeeds.

    Args:
        name: The metric name, e.g. `dlqs.dead_letters`.
        description: What the gauge measures.
        read: Returns the current value.
        unit: The unit of the value, following the UCUM codes OpenTelemetry uses.
        interval: Seconds between the end of one call to `read` and the next.
        timeout: Seconds after which a call to `read` is abandoned.
        meter: The meter to create the gauge with; defaults to one from the global
            MeterProvider.
    """
    meter = meter or get_meter(__name__)
    gauge = meter.create_gauge(name, unit=unit, description=description)

    async def refresh() -> None:
        while True:
            try:
                async with asyncio.timeout(timeout):
                    value = await read()
            except Exception as error:
                log.warning("Could not refresh gauge %s: %r", name, error)
            else:
                gauge.set(value)
            await asyncio.sleep(interval)

    task = asyncio.create_task(refresh(), name=f"refresh_gauge:{name}")
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
