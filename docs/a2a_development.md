# Agent-to-Agent (A2A) Development Guide

This document outlines the patterns and best practices for developing and interacting with A2A agents within the AutoSRE system on Vertex AI Reasoning Engine.

## Overview

The A2A protocol enables structured communication between agents. In AutoSRE, we use it for communication between the `sre-helper` and `o11y-agent`.

## 1. REST Payload Structure for Vertex AI

When interacting with a deployed A2A agent on Vertex AI Reasoning Engine via direct REST calls (e.g., from outside the SDK or when SDK models mismatch), use the following payload structure for the `/v1/message:send` endpoint:

```json
{
  "message": {
    "role": "1",
    "content": [
      {
        "text": "Your query here"
      }
    ],
    "contextId": "...",
    "messageId": "..."
  }
}
```

**Critical Constraints:**
*   **`role`**: Must be `"1"` (string containing the enum value for USER). Do not use `"user"`.
*   **`content`**: Must be a list of objects, each containing a `text` field. Do not use `parts`.

## 2. AgentExecutor Implementation

To bridge an ADK agent with the A2A protocol, implement a custom `AgentExecutor`. This class is responsible for:
1.  Receiving the A2A `RequestContext`.
2.  Initializing or retrieving the ADK `Runner`.
3.  Executing the agent logic via `runner.run_async`.
4.  Updating task status and adding artifacts via `TaskUpdater`.

Example structure:
```python
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.tasks import TaskUpdater

class MyAgentExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.submit()
        await updater.start_work()
        
        query = context.get_user_input()
        # Drive ADK Runner and send updates to updater
        ...
        await updater.complete()
```

## 3. Deployment

When deploying an agent that needs to expose A2A endpoints on Vertex AI:
*   Use `vertexai.preview.reasoning_engines.templates.a2a.A2aAgent` as the template.
*   Do **not** wrap the agent in `AdkApp` during deployment, as this can mask the native A2A endpoints.

## 4. Local vs Remote Setup

The system supports both local development and remote production modes, controlled by the `LOCAL_A2A` environment variable.

### Local Setup
In local mode, agents communicate via the standard A2A SDK clients over HTTP/JSON-RPC.

1.  **Start Target Agent (e.g., `o11y-agent`)**:
    Run the A2A server using Uvicorn:
    ```bash
    cd o11y-agent
    .venv/bin/python -m uvicorn app.a2a_server:a2a_app --host 0.0.0.0 --port 10000
    ```
2.  **Configure Calling Agent (e.g., `sre-helper`)**:
    Set `LOCAL_A2A=True` in the environment. The wrapper will use `A2AClient` to connect to `http://localhost:10000`.

### Remote Setup
In remote mode, agents communicate via direct REST calls to the Vertex AI Reasoning Engine endpoints.

1.  **Target Agent**: Deployed to Vertex AI Reasoning Engine (exposing `/a2a/v1/...` endpoints).
2.  **Calling Agent**: Set `LOCAL_A2A=False` (or unset it). The wrapper will use `httpx.AsyncClient` to send POST requests to the Reasoning Engine URL with the strict Protobuf-compliant payload described in Section 1.

## 5. Testing

### Unit and Integration Tests
Run tests using `pytest` within the respective agent directory.

Example for `sre-helper`:
```bash
cd sre-helper
.venv/bin/python -m pytest tests/integration/test_a2a.py
```
*Note: Tests should mock the A2A calls to avoid dependency on running servers or remote endpoints.*

### End-to-End Local Verification
To verify the actual communication between agents locally:
1.  Start the `o11y-agent` server on port 10000 (see Local Setup).
2.  Run the test script in `sre-helper`:
    ```bash
    cd sre-helper
    .venv/bin/python run_a2a_test.py
    ```
    This script sets `LOCAL_A2A=True` and sends a query that triggers the `o11y_agent` tool, verifying the full roundtrip.

## 6. Agent Engine A2A Testing Baseline (Updated April 15, 2026)

The `sre-helper` project now includes a minimum viable test baseline aligned with
the current A2A-first architecture:

1. **Agent Engine compatibility export**
   - `app.agent` exposes `get_app()` that returns the exported A2A app object.
   - This keeps `app.agent_engine_app` import-compatible while preserving the
     `A2aAgent` runtime model.

2. **Current-architecture integration tests**
   - `tests/integration/test_agent.py` validates that `get_app()` resolves to an
     `A2aAgent`.
   - `tests/integration/test_agent_engine_app.py` validates feedback and operation
     registration without depending on stale `root_agent` symbols.

3. **Transport-level A2A wrapper validation**
   - `tests/integration/test_a2a.py` now exercises both wrapper branches:
     - local A2A (`A2AClient` flow),
     - remote Reasoning Engine REST (`message:send` + task polling flow),
     using deterministic mocks.

4. **Runtime `LOCAL_A2A` evaluation**
   - The wrapper checks `config.is_local_a2a()` at call time.
   - Tests can switch behavior with environment variables plus module reload.

5. **Portable local server bootstrap**
   - `sre-helper/app/a2a_server.py` no longer depends on a developer-specific
     absolute `.env` path and uses regular `load_dotenv()`.
