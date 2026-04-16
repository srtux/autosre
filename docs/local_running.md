# Local Running and Multi-Process A2A Testing

To test the multi-agent system locally with production-parity, we stand up independent agent servers and verify the end-to-end A2A (Agent-to-Agent) protocol flow.

## Running the Agents

Instead of using in-memory mocks, we run the specialist agent as a separate process and call it from the orchestrator agent.

### Prerequisites

Ensure dependencies are installed in both directories:
```bash
cd sre-helper
uv sync
cd ../o11y-agent
uv sync
```

#### Environment Variables
The `o11y-agent` resolves its four MCP toolsets from Agent Registry. Each toolset ID can be overridden via an env var, and `GOOGLE_CLOUD_PROJECT` must always be set. Copy `.env.example` to `.env` and fill in the values.

Example `.env` file content:
```env
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_CLOUD_STORAGE_BUCKET=your-staging-bucket

LOGGING_MCP_SERVER_ID=projects/your-project-id/locations/global/mcpServers/your-logging-mcp-server-id
TRACE_MCP_SERVER_ID=projects/your-project-id/locations/global/mcpServers/your-trace-mcp-server-id
MONITORING_MCP_SERVER_ID=projects/your-project-id/locations/global/mcpServers/your-monitoring-mcp-server-id
ERROR_REPORTING_MCP_SERVER_ID=projects/your-project-id/locations/global/mcpServers/your-error-reporting-mcp-server-id
```

### Step 1: Start the Observability Agent Server

Run the `o11y-agent` as a uvicorn ASGI server on port **10000**. From the `o11y-agent` directory:

```bash
uv run uvicorn app.a2a_server:a2a_app_factory --factory --port 10000
```

The `--factory` flag tells uvicorn to call `a2a_app_factory()` to build the ASGI app lazily — this keeps agent construction off the import path so module import stays side-effect-free (see [deployment_patterns.md §3](deployment_patterns.md#3-keep-module-import-side-effect-free)). The A2A endpoints are mounted at `/a2a/app`.

### Step 2: Run the SRE Helper Integration Tests

From the `sre-helper` directory, run the integration test suite via pytest:

```bash
uv run pytest tests/integration -q
```

The tests hit the locally-running `o11y-agent` over A2A — there is no mock layer.

## How it Works

As of the latest refactor, `sre-helper` resolves the `o11y-agent` using the official `AgentRegistry` and wires it into `sub_agents`. The previous logic involving `LOCAL_A2A` environment variables and local file resolution of Agent Cards has been removed.

## Deployment to Agent Engine

To deploy the agents to Vertex AI Agent Engine (Reasoning Engine), use each agent's own `deploy.py`. There is no longer a shared `scripts/deploy.py`. Both scripts require `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_STORAGE_BUCKET` to be set (via `.env`).

### Deploying o11y-agent

From the `o11y-agent` directory:
```bash
uv sync
uv run python deploy.py
```

### Deploying sre-helper

From the `sre-helper` directory:
```bash
uv sync
uv run python deployment/deploy.py
```

### A2A Discovery in Production

When deployed, the `sre-helper` resolves the `o11y-agent` using Cloud `AgentRegistry` dynamically, provided it is registered as an A2A service in the project.

## Code Quality and Linting

We use `ruff` for linting and code formatting. It is part of the dev dependencies in both projects, so invoke via `uv run`.

To run the linter in `sre-helper`:
```bash
cd sre-helper
uv run ruff check .
```

To auto-fix fixable errors:
```bash
uv run ruff check . --fix
```

You can also run it on `o11y-agent`:
```bash
cd o11y-agent
uv run ruff check .
```
