# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Prometheus metrics endpoint, served on its own port outside the REST app.

Kept off the REST app's router/port deliberately: `dlqs` does its own bearer-token
auth and is not covered by the gateway's session-based ext-authz, so anything
registered on the REST app's router is reachable through the public HTTPRoute.
Serving metrics on a separate port that the HTTPRoute never references means the
public edge has no path to it at all, regardless of app-level auth.
"""

import asyncio
import logging

from prometheus_client import REGISTRY, start_http_server
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector

from dlqs.config import Config
from dlqs.ports.inbound.dlq_manager import DLQManagerPort

log = logging.getLogger(__name__)


class DeadLetterCollector(Collector):
    """Reports the current number of stored dead letter events.

    `collect()` is called by the metrics server on its own thread, so the count is
    fetched from the DAO by handing the coroutine to the main event loop and
    blocking this thread until it completes.
    """

    def __init__(self, *, dlq_manager: DLQManagerPort, loop: asyncio.AbstractEventLoop):
        self._dlq_manager = dlq_manager
        self._loop = loop

    def collect(self):  # noqa: D102
        count = asyncio.run_coroutine_threadsafe(
            self._dlq_manager.count_dead_letters(), self._loop
        ).result(timeout=10)
        yield GaugeMetricFamily(
            "dlqs_dead_letters_total",
            "Current number of events stored in the dead letter queue.",
            value=count,
        )


def start_metrics_server(*, config: Config, dlq_manager: DLQManagerPort) -> None:
    """Start the Prometheus metrics HTTP server in a background thread.

    Only safe with a single worker process: `start_http_server` binds a port in
    the calling process, so with `workers > 1` every worker but the first would
    fail to bind it. Logs an error and does nothing instead of starting when
    `workers != 1`.
    """
    if config.workers != 1:
        log.error(
            "Not starting the metrics server: only supported with a single worker "
            "process, but workers=%s.",
            config.workers,
        )
        return

    loop = asyncio.get_running_loop()
    REGISTRY.register(DeadLetterCollector(dlq_manager=dlq_manager, loop=loop))
    start_http_server(port=config.metrics_port, addr=config.host)
    log.info("Metrics server listening on %s:%s", config.host, config.metrics_port)
