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

"""Tests for the metrics setup in `configure_opentelemetry`."""

import pytest
from opentelemetry import metrics, trace
from opentelemetry.metrics import _internal as metrics_internal
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader, NumberDataPoint
from opentelemetry.sdk.resources import SERVICE_INSTANCE_ID, SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.util._once import Once

from hexkit.opentelemetry import (
    OpenTelemetryConfig,
    configure_opentelemetry,
    instrumentation,
)

SERVICE_NAME_VALUE = "test-service"


@pytest.fixture(autouse=True)
def reset_global_providers(monkeypatch: pytest.MonkeyPatch):
    """Let each test set the global providers, which OpenTelemetry allows only once."""
    monkeypatch.setattr(trace, "_TRACER_PROVIDER", None)
    monkeypatch.setattr(trace, "_TRACER_PROVIDER_SET_ONCE", Once())
    monkeypatch.setattr(metrics_internal, "_METER_PROVIDER", None)
    monkeypatch.setattr(metrics_internal, "_METER_PROVIDER_SET_ONCE", Once())


def configure(**config_values) -> InMemoryMetricReader:
    """Configure OpenTelemetry with in-memory exporters and return the metric reader."""
    reader = InMemoryMetricReader()
    configure_opentelemetry(
        service_name=SERVICE_NAME_VALUE,
        config=OpenTelemetryConfig(**config_values),
        span_processor=SimpleSpanProcessor(InMemorySpanExporter()),
        metric_readers=[reader],
    )
    return reader


def test_metrics_are_off_by_default():
    """Enabling OpenTelemetry alone must not set up a MeterProvider."""
    configure(enable_opentelemetry=True)

    assert not isinstance(metrics.get_meter_provider(), MeterProvider)


def test_metrics_need_opentelemetry_enabled():
    """The metrics flag does nothing while OpenTelemetry as a whole is disabled."""
    configure(enable_opentelemetry=False, enable_otel_metrics=True)

    assert not isinstance(metrics.get_meter_provider(), MeterProvider)


def test_metrics_are_recorded_with_service_name():
    """A gauge set after configuration reaches the reader with the service resource."""
    reader = configure(enable_opentelemetry=True, enable_otel_metrics=True)

    assert isinstance(metrics.get_meter_provider(), MeterProvider)
    gauge = metrics.get_meter(__name__).create_gauge("test.gauge")
    gauge.set(42)

    data = reader.get_metrics_data()
    assert data is not None
    (resource_metrics,) = data.resource_metrics
    assert resource_metrics.resource.attributes[SERVICE_NAME] == SERVICE_NAME_VALUE
    (gauge_metric,) = [
        metric
        for scope_metrics in resource_metrics.scope_metrics
        for metric in scope_metrics.metrics
        if metric.name == "test.gauge"
    ]
    (point,) = gauge_metric.data.data_points
    assert isinstance(point, NumberDataPoint)
    assert point.value == 42


def recorded_resource(reader: InMemoryMetricReader) -> Resource:
    """Record one gauge value and return the resource it was exported with."""
    metrics.get_meter(__name__).create_gauge("test.gauge").set(1)
    data = reader.get_metrics_data()
    assert data is not None
    (resource_metrics,) = data.resource_metrics
    return resource_metrics.resource


def test_each_process_has_an_instance_id():
    """Metrics carry a service.instance.id, so replicas stay separate series."""
    reader = configure(enable_opentelemetry=True, enable_otel_metrics=True)

    resource = recorded_resource(reader)
    assert resource.attributes[SERVICE_NAME] == SERVICE_NAME_VALUE
    assert resource.attributes[SERVICE_INSTANCE_ID]


def test_instance_id_added_when_sdk_lacks_it(monkeypatch: pytest.MonkeyPatch):
    """SDK versions whose Resource.create adds no instance ID still get one."""
    monkeypatch.setattr(
        instrumentation.Resource,
        "create",
        staticmethod(lambda attributes: Resource(attributes)),
    )
    reader = configure(enable_opentelemetry=True, enable_otel_metrics=True)

    assert recorded_resource(reader).attributes[SERVICE_INSTANCE_ID]


def test_resource_attributes_from_environment(monkeypatch: pytest.MonkeyPatch):
    """OTEL_RESOURCE_ATTRIBUTES is merged, e.g. for a readable pod name."""
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "k8s.pod.name=dlqs-rest-abc12")
    reader = configure(enable_opentelemetry=True, enable_otel_metrics=True)

    resource = recorded_resource(reader)
    assert resource.attributes["k8s.pod.name"] == "dlqs-rest-abc12"
    assert resource.attributes[SERVICE_NAME] == SERVICE_NAME_VALUE
