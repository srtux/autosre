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

## 6. Known Blockers for Agent Engine A2A Testing

The following issues currently prevent reliable validation of A2A behavior in the
`sre-helper` Agent Engine path:

1. **`app.agent_engine_app` imports a missing symbol**
   - The module imports `get_app` from `app.agent`, but `app/agent.py` only exports
     the A2A `app` object and helper functions.
   - Impact: Agent Engine import/setup can fail before any A2A test logic runs.

2. **Integration tests reference stale agent symbols**
   - `tests/integration/test_agent.py` and
     `tests/integration/test_agent_engine_app.py` import `root_agent` from
     `app.agent`, but `root_agent` is no longer defined in the current A2A-first
     implementation.
   - Impact: Tests target an outdated architecture and do not exercise the current
     code paths.

3. **`test_a2a.py` does not test real A2A transport**
   - The test defines an inline `o11y_agent` Python function and wires it directly
     as a tool, rather than invoking `make_a2a_wrapper()` and validating JSON-RPC
     or Reasoning Engine REST behavior.
   - Impact: Passing results do not prove A2A communication works.

4. **Local A2A mode is effectively static at import-time**
   - `LOCAL_A2A` is computed once in `app_utils/config.py` and imported as a module
     constant in `app/agent.py`.
   - Impact: Runtime `monkeypatch.setenv("LOCAL_A2A", ...)` in tests may not change
     behavior unless modules are reloaded in a controlled way.

5. **Hardcoded local `.env` path in `sre-helper/app/a2a_server.py`**
   - The file requires `/Users/summitt/work/autosre/.env`.
   - Impact: Running in CI/containers fails before app startup, blocking local A2A
     smoke testing.

To make Agent Engine A2A testing meaningful, align tests with the current
`A2aAgent` architecture, remove stale symbol imports, and validate both local
(`A2AClient`) and remote (`message:send` + task polling) paths with deterministic
HTTP mocks.
