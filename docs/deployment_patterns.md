# Deployment Patterns and Troubleshooting

This document captures the lessons learned and solutions applied during the deployment of AutoSRE agents to Vertex AI Agent Engine (Reasoning Engine).

## 1. ModuleNotFoundError: No module named 'app.agent'

### The Problem
When deploying agents using the Vertex AI SDK (`client.agent_engines.create`), the source code is packaged and uploaded. If the local directory structure is not preserved exactly during pickling, `cloudpickle` may fail to resolve module paths in the remote container, leading to `ModuleNotFoundError`.

This is common when using `extra_packages` or staging files in a way that flattens the directory structure.

### The Solution: The "Temp Directory Trick"
To ensure that `cloudpickle` preserves the full module path (e.g., `app.agent`), we use a structured temporary directory during deployment:

1.  Create a temporary directory.
2.  Recreate the desired package structure inside it (e.g., `temp_dir/app/...`).
3.  Add `temp_dir` to `sys.path` before importing the agent object.
4.  Perform the deployment using the Vertex AI SDK.

Example implementation (see `o11y-agent/deploy.py` and `sre-helper/deployment/deploy.py` for the real scripts):
```python
import os
import shutil
import sys
import tempfile

# The staging dir must live OUTSIDE the source tree so we don't recursively
# copy our own temp dir. tempfile.TemporaryDirectory() gives us that plus
# guaranteed cleanup.
with tempfile.TemporaryDirectory() as tmp_dir:
    # Recreate the `app/` package path so `cloudpickle` sees `app.agent`
    # rather than a flat module.
    app_src = os.path.join(os.path.dirname(__file__), "app")
    shutil.copytree(app_src, os.path.join(tmp_dir, "app"))

    # Force Python to resolve `app` from the staged copy.
    sys.path.insert(0, tmp_dir)
    from app import agent  # noqa: E402

    # Deploy using the imported agent object.
    # client.agent_engines.create(agent=agent.app, config={...})
```

Key points:
*   Use `tempfile.TemporaryDirectory()` — **not** `tempfile.mkdtemp(dir=agent_path)`. Creating the staging dir inside the agent source tree causes `shutil.copytree` to recurse into it.
*   Copy the `app/` package wholesale with `shutil.copytree` so the module path `app.agent` resolves in the remote container.
*   Insert the staging dir at the front of `sys.path` **before** importing the agent.

## 2. IAM Permissions for A2A and MCP Tools

### Agent Identity (SPIFFE)
Modern Reasoning Engine deployments use a per-agent SPIFFE identity (Workload Identity) rather than a standard service account. This allows for granular, resource-specific permissions.

The SPIFFE identity format:
`principal://agents.global.org-{ORGANIZATION_ID}.system.id.goog/resources/aiplatform/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{ENGINE_ID}`

### Required Roles
To enable full functionality, including Agent-to-Agent (A2A) calls and MCP tool usage, the following roles must be granted to the agent's identity:

*   **`roles/aiplatform.user`**: Essential for `aiplatform.reasoningEngines.query`. Required for **both** the caller (to invoke another agent) and the specialist (to call tools).
*   **`roles/agentregistry.viewer`**: Required to resolve remote agents and MCP servers by name in the discovery service.
*   **`roles/mcp.toolUser`**: Required to invoke MCP tools.
*   **`roles/logging.viewer`**: Required to query Cloud Logging.
*   **`roles/cloudtrace.viewer`**: Required for the Cloud Trace MCP server.
*   **`roles/monitoring.viewer`**: Required for the Monitoring MCP server.
*   **`roles/errorreporting.viewer`**: Required for the Error Reporting MCP server.

### Setup Script
Use `scripts/setup_iam.sh` to automate the granting of these roles. Note that `roles/aiplatform.user` was added to this script to support A2A communication.

## 3. Keep Module Import Side-Effect Free

### The Problem
Vertex AI Agent Engine cold-starts a container and then imports your agent
module so cloudpickle can rehydrate the exported `app` object. Anything your
module does at import time — `google.auth.default()`, `AgentRegistry(...)`,
MCP toolset resolution, network calls — runs before the runtime environment
is guaranteed to be ready. A missing `GOOGLE_CLOUD_PROJECT`, a boot-order
race on IAM, or a transient registry error will then surface as a cryptic
cold-start import failure, not a runtime error from the first request.

### The Rule
Top-level module code in a deployed agent must only do pure Python work:
imports, class and function definitions, `load_dotenv()`, dataclass
literals, and constructing the `A2aAgent` / `AdkApp` export itself.
Everything that touches auth, registry, or the network goes inside a lazy
builder that runs on first `execute()`.

### Pattern
```python
_ops_agent: Agent | None = None

def get_ops_agent() -> Agent:
    global _ops_agent
    if _ops_agent is not None:
        return _ops_agent
    project_id = _resolve_project_id()   # lazily imports google.auth
    registry = AgentRegistry(project_id=project_id, location="global")
    _ops_agent = Agent(..., tools=[registry.get_mcp_toolset(...)])
    return _ops_agent

class MyExecutor(AgentExecutor):
    def __init__(self):
        self._runner = None
    def _init_adk(self):
        if self._runner is None:
            self._runner = Runner(agent=get_ops_agent(), ...)
        return self._runner
    async def execute(self, context, event_queue):
        runner = self._init_adk()
        ...
```

This is the pattern used in `o11y-agent/app/agent.py`. Copy it for any new
agent.

## 4. Current State (April 2026)

### Active Agents
*   **`o11y-agent`**: A single `OpsAgent` with four MCP toolsets — Logging, Trace, Monitoring, and Error Reporting.
*   **`sre-helper`**: Orchestrator agent that uses A2A (via `AgentRegistry` + `sub_agents`) to delegate to `o11y-agent`.

### Deployed Instances
Deployed Reasoning Engine IDs are not checked in. Track them per-environment via env vars, the Agent Engine list in the Cloud Console, or `gcloud alpha ai reasoning-engines list`. Both agents are deployed with `identity_type=AGENT_IDENTITY`, and IAM bindings are applied via `scripts/setup_iam.sh` against each engine's SPIFFE principal.
