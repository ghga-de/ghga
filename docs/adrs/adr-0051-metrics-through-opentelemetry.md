---
status: proposed
date: 2026-11-24
tags: [backend, deploy]
---

# ADR-0051 — Services export metrics through OpenTelemetry

## Summary

In the context of **services that need metrics, starting with the number of events in the DLQ**

facing **counters that are recorded inline, and gauges whose value lives in a database the exporter cannot await**

we decided for **pushing metrics via OTLP through hexkit's OpenTelemetry setup, and reading async gauge sources in a background task whose cached value an observable gauge reports (`refresh_gauge`)**

and neglected **a Prometheus endpoint per service with `prometheus_client`, and querying the database from the gauge callback**

to achieve **one setup, one collector and one resource for traces and metrics, without an extra port or thread per service**

accepting that **the collector needs a metrics pipeline, aggregation moves to query time, the instrumented libraries' metrics come along, and a gauge reports a value up to one interval old**.

## Details

### Context

The first request was a gauge for the events stored in the DLQ.
A pull request (#220) added a Prometheus endpoint to the DLQ service with `prometheus_client`.
Its collector ran on the scrape thread and had to block on the event loop for the MongoDB count, which deadlocked once a scrape ran on the loop's own thread.
Other services will want metrics too, so the choice belongs in the libraries, not in one service.

hexkit already sets up OpenTelemetry for tracing, configured through the standard `OTEL_*` variables and sending OTLP to a collector.

### Decision

Metrics go through the same OpenTelemetry setup as traces.
`configure_opentelemetry` sets up a `MeterProvider` that pushes via OTLP when `enable_otel_metrics` is on, and it is off by default.
Services record metrics through the OpenTelemetry API, which hands out no-op instruments while metrics are off.

Every process gets its own `service.instance.id`, which Prometheus sees as the `instance` label, so replicas and workers never share a series.
The common chart adds `k8s.pod.name` to the resource.

Counters and histograms are recorded inline where things happen.
A value read from an async source, such as a database, is reported through `refresh_gauge` from ghga-service-commons: a task on the event loop awaits the read every interval and caches the value with its read time, and an observable gauge's callback, which runs on the exporter thread, only reports that cached value.
The gauge reports nothing before the first read and once the value is older than three intervals, so the series goes absent instead of going stale.

### Consequences

- The collector needs a metrics pipeline, for example the `prometheus` exporter that a Prometheus server scrapes.
- Every replica reports its own series, so queries aggregate: `sum(rate())` for counters and histograms, `max()` for a gauge every replica reads from the same source.
- Turning metrics on also exports what the instrumented libraries record, such as FastAPI's and httpx's HTTP metrics.
- A gauge lags its source by up to one interval, 30 seconds by default, and each replica runs the read.
- A gauge name can be used once per meter and process, since OpenTelemetry cannot remove a gauge; `refresh_gauge` raises on a second one.
- The endpoint approach of #220 is not taken up again.

### Alternatives

- **`prometheus_client` with an endpoint per service.**
  Every service would need a port, an HTTP server thread and a chart change, next to a second telemetry setup.
  Its collectors are synchronous too, so the database problem stays.
- **Querying the database in the observable gauge callback.**
  The callback runs on the exporter thread and cannot await; bridging into the event loop blocks the exporter and deadlocks when a collection runs on the loop's thread.
- **A synchronous gauge set by the background task.**
  It keeps the last value forever, so a failing read would show an outdated number as current.
