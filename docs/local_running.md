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

1.  **Agent Card**: The `o11y-agent/app/agent.json` file defines the Agent Card, specifying the name, version, and the full RPC URL (`http://localhost:8005/a2a/app`).
2.  **Remote Resolution**: In `sre-helper/app/agent.py`, when `LOCAL_A2A="True"` is set, the agent resolves the child agent using `RemoteA2aAgent` pointing to the local file path of the Agent Card.
3.  **A2A Protocol**: The `RemoteA2aAgent` handles the HTTP communication with the server on port 8005 following the standard A2A protocol.

## Deployment to Agent Engine

To deploy the agents to Vertex AI Agent Engine (Reasoning Engine), use the `agents-cli deploy` command.

### Prerequisites

Ensure you have the correct project and region set:
```bash
gcloud config set project <your-project-id>
```

### Deploying o11y-agent

From the `o11y-agent` directory:
```bash
uv run agents-cli deploy --project=<your-project-id> --region=<your-region>
```
> [!IMPORTANT]
> The `o11y-agent` requires a file named `app/agent_engine_app.py` exposing `agent_engine` (an instance of `AdkApp`) for successful introspection during deployment.
> Also, ensure that agents requiring missing registry tools (like Trace and Metrics) are commented out in `app/agent.py` during load to avoid introspection failures.

### Deploying sre-helper

From the `sre-helper` directory:
```bash
uv run agents-cli deploy --project=<your-project-id> --region=<your-region>
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

