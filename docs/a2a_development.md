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

## 4. Current A2A Communication Pattern

As of the latest refactor, A2A communication between `sre-helper` and `o11y-agent` is handled using the official `AgentRegistry` and `sub_agents` pattern provided by the ADK.

### Implementation Details
*   **Registry Resolution**: `sre-helper` uses `AgentRegistry(project_id="agent-o11y", location="us-central1")` to resolve the remote agent.
*   **Sub-Agents**: The resolved agent is added to the `sub_agents` list of the root agent, allowing for direct delegation without custom tool wrappers or manual HTTP calls.

The previous custom wrapper logic and the `LOCAL_A2A` environment variable have been removed to align with the official SDK patterns.
