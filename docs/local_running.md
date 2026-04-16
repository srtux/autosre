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
The `o11y-agent` requires the `LOGGING_MCP_SERVER_ID` environment variable to be set. This should point to the full resource name of the MCP server in the Agent Registry.

Example `.env` file content:
```env
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
LOGGING_MCP_SERVER_ID=projects/your-project-id/locations/global/mcpServers/your-mcp-server-id
```

### Step 1: Start the Observability Agent Server

Run the `o11y-agent` as an API server with A2A enabled. From the `o11y-agent` directory:

```bash
uv run adk api_server --a2a --port=8005 ./
```

This command will scan the current directory, find the `app` folder (which contains `agent.json`), and mount the A2A endpoints at `/a2a/app`.

### Step 2: Run the SRE Helper Test

We use a clean test script in `sre-helper` that does not use mocks and calls the remote agent via the A2A protocol.

From the `sre-helper` directory:

```bash
uv run run_a2a_test.py
```

## How it Works

As of the latest refactor, `sre-helper` resolves the `o11y-agent` using the official `AgentRegistry` and `sub_agents` pattern. The previous logic involving `LOCAL_A2A` environment variables and local file resolution of Agent Cards has been removed.

## Deployment to Agent Engine

To deploy the agents to Vertex AI Agent Engine (Reasoning Engine), use the custom `deploy.py` script.

### Deploying o11y-agent

From the `o11y-agent` directory:
```bash
uv sync
uv run python ../scripts/deploy.py .
```

### Deploying sre-helper

From the `sre-helper` directory:
```bash
uv sync
uv run python ../scripts/deploy.py .
```

### A2A Discovery in Production

When deployed, the `sre-helper` will resolve the `o11y-agent` using the Cloud `AgentRegistry` dynamically, provided it is registered as an A2A service in the project.

## Code Quality and Linting

We use `ruff` for linting and code formatting in this project.

To run the linter in `sre-helper`:
```bash
cd sre-helper
uvx ruff check .
```

To auto-fix fixable errors:
```bash
uvx ruff check . --fix
```

You can also run it on `o11y-agent`:
```bash
cd o11y-agent
uvx ruff check .
```

