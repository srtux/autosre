# sre-helper

Orchestrator root agent for AutoSRE. Built on Google ADK and uses A2A to
delegate observability investigation to `o11y-agent`.

## Requirements

- **uv**: Python package manager — [install](https://docs.astral.sh/uv/getting-started/installation/)
- **Google Cloud SDK** with application default credentials configured
- `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_STORAGE_BUCKET` env vars for deployment

## Quick Start

Install dependencies:

```bash
uv sync
```

Start the downstream `o11y-agent` in a separate terminal (see
[`../o11y-agent/README.md`](../o11y-agent/README.md) for details — it listens
on port `10000` by default).

Run the integration tests:

```bash
uv run pytest tests/integration -q
```

## Deploy

Deploy to Vertex AI Agent Engine:

```bash
export GOOGLE_CLOUD_PROJECT=<your-project-id>
export GOOGLE_CLOUD_STORAGE_BUCKET=<your-staging-bucket>
uv run python deployment/deploy.py
```

Delete a deployed instance:

```bash
uv run python deployment/deploy.py --delete <resource_id>
```

## Project Layout

- `sre_helper/agent.py` — orchestrator `Agent` + `AgentEngineApp` (lazy-built).
- `sre_helper/app_utils/` — feedback schema, telemetry, config helpers.
- `deployment/deploy.py` — Vertex AI Agent Engine deployment.
- `tests/integration/` — pytest suite.

## Documentation

- [System Architecture](../docs/architecture.md)
- [Local Running](../docs/local_running.md)
- [Deployment Patterns](../docs/deployment_patterns.md)
