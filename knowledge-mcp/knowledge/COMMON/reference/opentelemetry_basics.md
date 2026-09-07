---
id: OTEL_REFERENCE
title: OpenTelemetry incident investigation reference
subsystem: COMMON
knowledge_type: reference
tags: [opentelemetry, traces, metrics, logs]
trust_level: evidence
---

# OpenTelemetry investigation

Use service metrics to identify the affected route, traces to follow failed requests across services,
and logs to inspect concrete exceptions. Correlate telemetry with deployment timestamps before diagnosis.
