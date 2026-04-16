# Observability Agent (o11y-agent)

Specialist observability agent for the AutoSRE system. A single ADK
`OpsAgent` backed by four Google Cloud MCP toolsets (Logging, Trace,
Monitoring, Error Reporting), exposed as an A2A server and deployable to
Vertex AI Agent Engine.

## Structure

- `app/agent.py` - lazy-built `OpsAgent` (`get_ops_agent()`) plus the A2A
  `O11yAgentExecutor` that drives the ADK `Runner`.
- `app/a2a_server.py` - uvicorn factory (`a2a_app_factory`) that builds the
  A2A ASGI app on boot, not at import time.
- `app/agent_engine_app.py` - `AgentEngineApp(AdkApp)` subclass with
  telemetry, Cloud Logging, and a `register_feedback` operation, plus the
  `get_app()` factory used by the deploy script.
- `app/agent.json` - static agent card advertising `skill: investigate_logs`
  at `http://localhost:10000/a2a/app`.
- `deploy.py` - Vertex AI Agent Engine deployment script (uses the
  "Temp Directory Trick" from `../docs/deployment_patterns.md`).

## Local usage

From the `o11y-agent/` directory:

```bash
uv sync
uv run uvicorn app.a2a_server:a2a_app_factory --factory --port 10000
```

The `--factory` flag is important - it tells uvicorn to call
`a2a_app_factory()` lazily when the server boots, so agent construction
(auth, registry lookups, MCP toolset resolution) never happens at module
import time.

## Deployment

```bash
export GOOGLE_CLOUD_PROJECT=<your-project>
export GOOGLE_CLOUD_STORAGE_BUCKET=<your-staging-bucket>
# GOOGLE_CLOUD_LOCATION is optional (defaults to us-central1).
uv run python deploy.py
```

The script deploys with `identity_type=AGENT_IDENTITY`, so a per-agent
SPIFFE identity is provisioned automatically. To delete a deployed
instance:

```bash
uv run python deploy.py --delete <resource_id>
```

See `../docs/architecture.md` for the broader system context and
`../docs/deployment_patterns.md` for deployment / IAM details.
