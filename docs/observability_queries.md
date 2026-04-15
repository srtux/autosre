# Observability Query Guidelines

This document outlines the query languages and filter syntaxes used by the observability agents to interact with Google Cloud services via MCP.

## Cloud Logging

Agents querying logs should use the **Logging Query Language**.

### Key Rules:
- **Boolean Operators**: `AND`, `OR`, `NOT` must be capitalized. Lowercase `and`, `or`, `not` are treated as search terms.
- **Comparisons**: Formatted as `[FIELD_NAME] [OP] [VALUE]`.
- **Operators**: `=`, `:`, `>=`, `<=`, `>`, `<`, `=~` (regex match), `!~` (regex not match).
- **Common Fields**: `resource.type`, `severity`, `textPayload`, `jsonPayload`.

### Example:
```
resource.type="gce_instance" AND severity>=ERROR
```

## Cloud Trace

Agents querying traces should use the filter syntax supported by the Cloud Trace API.

### Key Filters:
- **Latency**: `latency:>1s`
- **Span Name**: `root:name`
- **Labels**: `has_label:key`

## Cloud Monitoring

Agents querying metrics should use **PromQL** or **ListTimeSeries filter syntax**.

### PromQL
Use standard PromQL syntax for querying metrics if supported by the environment.
Example:
```promql
sum(rate(http_requests_total[5m]))
```

### ListTimeSeries Filter Syntax
When using the ListTimeSeries API, use the filter syntax specified by Google Cloud.
Filters are typically of the form `[FIELD] = [VALUE]` and can be combined with `AND`.

Example:
```
metric.type = "compute.googleapis.com/instance/cpu/utilization" AND resource.type = "gce_instance"
```
