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
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from contextlib import asynccontextmanager, suppress

from opentelemetry.metrics import CallbackOptions, Meter, Observation, get_meter

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
    max_age: float | None = None,
    meter: Meter | None = None,
) -> AsyncIterator[None]:
    """Report the value of an async source as a gauge while the context is open.

    OpenTelemetry calls the callback of an observable gauge from its exporter thread,
    where it cannot await, so it cannot query an async source such as a database
    itself. Instead, `read` is awaited on entry and then every `interval` seconds in a
    background task on the running event loop, and the callback only reports the last
    value that task read.

    A call that fails or takes longer than `timeout` seconds is logged as a warning
    and keeps the previous value. Once the last successful read is older than
    `max_age` seconds, the gauge reports nothing, so the series goes absent instead
    of showing an outdated value. After the context closes it reports nothing either.

    Args:
        name: The metric name, e.g. `dlqs.dead_letters`.
        description: What the gauge measures.
        read: Returns the current value.
        unit: The unit of the value, following the UCUM codes OpenTelemetry uses.
        interval: Seconds between the end of one call to `read` and the next.
        timeout: Seconds after which a call to `read` is abandoned.
        max_age: Seconds after which a value is too old to report; defaults to three
            intervals.
        meter: The meter to create the gauge with; defaults to one from the global
            MeterProvider.
    """
    meter = meter or get_meter(__name__)
    max_age = 3 * interval if max_age is None else max_age

    # The value and the monotonic time it was read at, replaced as one tuple, so the
    # exporter thread never pairs a value with the time of another read
    latest: tuple[float, float] | None = None

    def observe(_options: CallbackOptions) -> Iterable[Observation]:
        snapshot = latest
        if snapshot is None:
            return
        value, read_at = snapshot
        if time.monotonic() - read_at <= max_age:
            yield Observation(value)

    meter.create_observable_gauge(
        name, callbacks=[observe], unit=unit, description=description
    )

    async def refresh() -> None:
        nonlocal latest
        while True:
            try:
                async with asyncio.timeout(timeout):
                    latest = (await read(), time.monotonic())
            except Exception as error:
                log.warning("Could not refresh gauge %s: %r", name, error)
            await asyncio.sleep(interval)

    task = asyncio.create_task(refresh(), name=f"refresh_gauge:{name}")
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        # OpenTelemetry cannot unregister the callback, so silence it instead
        latest = None
